package com.example.medicofeeds.data

import android.util.Log
import com.example.medicofeeds.data.api.RetrofitClient
import com.example.medicofeeds.data.model.FeedItem
import com.google.firebase.auth.FirebaseAuth
import java.io.IOException

interface DataRepository {
    suspend fun getScholarlyFeed(page: Int, topic: String, userId: String?): List<FeedItem>
    suspend fun getGuidelinesFeed(page: Int, userId: String?): List<FeedItem>
    suspend fun markAsRead(userId: String, itemId: String)
    suspend fun toggleBookmark(userId: String, item: FeedItem, bookmarked: Boolean)
    suspend fun getBookmarks(userId: String): List<String>
    suspend fun getBookmarkedArticles(): List<FeedItem>
}

class DefaultDataRepository(private val context: android.content.Context) : DataRepository {
    private val gson = com.google.gson.Gson()
    private val sharedPrefs = context.getSharedPreferences("medguide_bookmarks", android.content.Context.MODE_PRIVATE)
    private val itemCache = java.util.concurrent.ConcurrentHashMap<String, FeedItem>()

    private fun getLocalBookmarksMap(): MutableMap<String, FeedItem> {
        val json = sharedPrefs.getString("bookmarks_map", null) ?: return mutableMapOf()
        return try {
            val type = object : com.google.gson.reflect.TypeToken<MutableMap<String, FeedItem>>() {}.type
            gson.fromJson(json, type) ?: mutableMapOf()
        } catch (e: Exception) {
            mutableMapOf()
        }
    }

    private fun saveLocalBookmarksMap(map: Map<String, FeedItem>) {
        val json = gson.toJson(map)
        sharedPrefs.edit().putString("bookmarks_map", json).apply()
    }

    override suspend fun getBookmarkedArticles(): List<FeedItem> {
        return getLocalBookmarksMap().values.toList()
    }

    override suspend fun getScholarlyFeed(page: Int, topic: String, userId: String?): List<FeedItem> {
        return try {
            val response = RetrofitClient.apiService.getScholarlyFeed(page, topic, userId)
            val items = response.articles?.map {
                FeedItem(
                    id = it.pmid,
                    title = it.title ?: "Untitled Research Article",
                    source = it.journal ?: "Medical Reference",
                    dateOrYear = it.year ?: "Recent",
                    summary = it.summary ?: "No AI clinical summary available.",
                    fullTextUrl = it.pubmed_url ?: "https://pubmed.ncbi.nlm.nih.gov/",
                    pdfUrl = it.pdf_url,
                    isGuideline = false
                )
            } ?: emptyList()
            items.forEach { itemCache[it.id] = it }
            items
        } catch (e: Exception) {
            Log.e("DefaultDataRepository", "Error fetching scholarly feed: ${e.message}", e)
            val mockItems = getMockScholarlyFeed(page, topic)
            mockItems.forEach { itemCache[it.id] = it }
            mockItems
        }
    }

    override suspend fun getGuidelinesFeed(page: Int, userId: String?): List<FeedItem> {
        return try {
            val response = RetrofitClient.apiService.getGuidelinesFeed(page, userId)
            val items = response.guidelines?.map {
                FeedItem(
                    id = it.link?.hashCode().toString() ?: it.title.hashCode().toString(),
                    title = it.title ?: "Untitled Guideline Alert",
                    source = it.source ?: "Medical Health Authority",
                    dateOrYear = it.published ?: "Recent",
                    summary = it.summary ?: "No AI clinical summary available.",
                    fullTextUrl = it.link ?: "https://www.who.int/",
                    pdfUrl = it.pdf_url,
                    isGuideline = true
                )
            } ?: emptyList()
            items.forEach { itemCache[it.id] = it }
            items
        } catch (e: Exception) {
            Log.e("DefaultDataRepository", "Error fetching guidelines feed: ${e.message}", e)
            val mockItems = getMockGuidelinesFeed(page)
            mockItems.forEach { itemCache[it.id] = it }
            mockItems
        }
    }

    override suspend fun markAsRead(userId: String, itemId: String) {
        try {
            RetrofitClient.apiService.markAsRead(com.example.medicofeeds.data.model.ReadRequest(userId, itemId))
        } catch (e: Exception) {
            // Fail silently in offline mode
        }
    }

    override suspend fun toggleBookmark(userId: String, item: FeedItem, bookmarked: Boolean) {
        try {
            val bookmarksMap = getLocalBookmarksMap()
            if (bookmarked) {
                bookmarksMap[item.id] = item
            } else {
                bookmarksMap.remove(item.id)
            }
            saveLocalBookmarksMap(bookmarksMap)
            
            RetrofitClient.apiService.toggleBookmark(com.example.medicofeeds.data.model.BookmarkRequest(userId, item.id, bookmarked))
        } catch (e: Exception) {
            // Fail silently in offline mode
        }
    }

    override suspend fun getBookmarks(userId: String): List<String> {
        return try {
            RetrofitClient.apiService.getBookmarks(userId).bookmarked_ids
        } catch (e: Exception) {
            getLocalBookmarksMap().keys.toList()
        }
    }

    private fun isNetworkException(e: Throwable): Boolean {
        return e is IOException || e is retrofit2.HttpException || e.message?.contains("Unable to resolve host") == true || e.message?.contains("failed to connect") == true
    }

    private fun getMockGuidelinesFeed(page: Int): List<FeedItem> {
        if (page > 1) return emptyList()
        return listOf(
            FeedItem(
                id = "mock_guide_1",
                title = "AAP Clinical Practice Guideline for the Evaluation and Treatment of Children and Adolescents with Obesity (2025)",
                source = "American Academy of Pediatrics (AAP)",
                dateOrYear = "2025",
                summary = "Recommends early pharmacological treatment and intensive health behavior lifestyle treatment (IHBLT) for pediatric obesity. Treatment decisions should start at age 6 with comprehensive family-based therapies, and pharmacotherapy should be considered for adolescents aged 12 and older.",
                fullTextUrl = "https://publications.aap.org/pediatrics",
                pdfUrl = "https://publications.aap.org/pediatrics",
                isGuideline = true
            ),
            FeedItem(
                id = "mock_guide_2",
                title = "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease",
                source = "KDIGO (Kidney Disease: Improving Global Outcomes)",
                dateOrYear = "2024",
                summary = "Integrates GFR and albuminuria stages for CKD progression risk assessment. Recommends SGLT2 inhibitors as first-line therapy for adults with CKD and heart failure or type 2 diabetes with eGFR >= 20 mL/min/1.73m2. Suggests RAS inhibitors at maximum tolerated doses for hypertension and severely increased albuminuria.",
                fullTextUrl = "https://kdigo.org/guidelines",
                pdfUrl = "https://kdigo.org/guidelines",
                isGuideline = true
            ),
            FeedItem(
                id = "mock_guide_3",
                title = "EULAR Recommendations for the Management of Rheumatoid Arthritis with Synthetic and Biological DMARDs (2024 Update)",
                source = "EULAR (European Alliance of Associations for Rheumatology)",
                dateOrYear = "2024",
                summary = "Recommends methotrexate as the first-line anchor drug therapy. Short-term glucocorticoids should be considered when initiating or changing conventional synthetic DMARDs, but must be tapered rapidly. If treatment target is not met, a biologic DMARD or JAK inhibitor should be added.",
                fullTextUrl = "https://www.eular.org",
                pdfUrl = "https://www.eular.org",
                isGuideline = true
            ),
            FeedItem(
                id = "mock_guide_4",
                title = "WHO Recommendations on the Management of Severe Malaria and Supportive Care (2025 Edition)",
                source = "World Health Organization (WHO)",
                dateOrYear = "2025",
                summary = "Strongly recommends intravenous artesunate as the preferred first-line treatment for adults and children with severe malaria. Pre-referral treatment with rectal artesunate is recommended for children under 6 years. Emphasizes blood glucose monitoring to prevent hypoglycemia.",
                fullTextUrl = "https://www.who.int",
                pdfUrl = "https://www.who.int",
                isGuideline = true
            ),
            FeedItem(
                id = "mock_guide_5",
                title = "ACOG Practice Bulletin: Clinical Management Guidelines for Gestational Hypertension and Preeclampsia",
                source = "ACOG (American College of Obstetricians and Gynecologists)",
                dateOrYear = "2024",
                summary = "Recommends low-dose aspirin (81 mg/day) initiation between 12 and 28 weeks of gestation for pregnant individuals at high risk of preeclampsia. Emphasizes delivery at 37 0/7 weeks for gestational hypertension or preeclampsia without severe features, and 34 0/7 weeks with severe features.",
                fullTextUrl = "https://www.acog.org",
                pdfUrl = "https://www.acog.org",
                isGuideline = true
            )
        )
    }

    private fun getMockScholarlyFeed(page: Int, topic: String): List<FeedItem> {
        if (page > 1) return emptyList()
        return when (topic.lowercase()) {
            "pediatrics" -> listOf(
                FeedItem(
                    id = "mock_sch_ped_1",
                    title = "Efficacy and Safety of RSV Prefusion F Protein Vaccine in Infants: A Randomized Controlled Trial",
                    source = "New England Journal of Medicine",
                    dateOrYear = "2024",
                    summary = "Phase 3 trial demonstrates that maternal immunization with RSVpreF vaccine significantly reduces the incidence of medically attended severe RSV-associated lower respiratory tract illness in infants through 150 days of life, with no safety signals identified.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_ped_2",
                    title = "Early Peanut Introduction in High-Risk Infants: 5-Year Allergy Outcomes",
                    source = "The Lancet",
                    dateOrYear = "2024",
                    summary = "Follow-up of the LEAP cohort confirms that early introduction of peanut products in infants with severe eczema or egg allergy leads to an 81% reduction in peanut allergy prevalence at age 5 compared to avoidance.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            "radiology" -> listOf(
                FeedItem(
                    id = "mock_sch_rad_1",
                    title = "Deep Learning AI System vs. Board-Certified Radiologists in Mammography Screening",
                    source = "Radiology",
                    dateOrYear = "2024",
                    summary = "Retrospective reader study shows that a deep learning algorithm achieved non-inferior sensitivity and superior specificity compared to board-certified breast radiologists for screening mammograms, significantly reducing false positive recall rates.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_rad_2",
                    title = "Low-Dose CT Screening for Lung Cancer: 10-Year Outcomes from the NELSON Trial",
                    source = "Journal of Clinical Oncology",
                    dateOrYear = "2023",
                    summary = "Long-term analysis confirms that volume CT lung screening in high-risk asymptomatic smokers reduces lung cancer mortality by 24% in men and 33% in women at 10 years, with a high positive predictive value for nodule detection.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            "dermatology" -> listOf(
                FeedItem(
                    id = "mock_sch_der_1",
                    title = "Efficacy of Oral JAK Inhibitors in Moderate-to-Severe Alopecia Areata: Phase 3 Trial Results",
                    source = "Journal of the American Academy of Dermatology",
                    dateOrYear = "2024",
                    summary = "Phase 3 clinical trial of baricitinib shows that a significantly higher proportion of patients achieved at least 80% scalp hair coverage at 36 weeks compared to placebo. Mild acne and headache were the most common adverse events.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_der_2",
                    title = "Dupilumab for Atopic Dermatitis in Pediatric Patients Aged 6 Months to 5 Years",
                    source = "JAMA Dermatology",
                    dateOrYear = "2024",
                    summary = "Randomized, double-blind study shows that dupilumab combined with low-potency topical corticosteroids significantly improved skin clearance and reduced itch severity in young children with moderate-to-severe atopic dermatitis, showing a favorable safety profile.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            "orthopedics" -> listOf(
                FeedItem(
                    id = "mock_sch_ort_1",
                    title = "Platelet-Rich Plasma vs. Intra-articular Corticosteroids for Mild-to-Moderate Knee Osteoarthritis",
                    source = "The American Journal of Sports Medicine",
                    dateOrYear = "2024",
                    summary = "A double-blind randomized controlled trial shows that intra-articular PRP injections achieved significantly better improvements in WOMAC pain scores and physical function at 12 months compared to corticosteroid injections.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_ort_2",
                    title = "Clinical Outcomes of Robotic-Assisted vs. Manual Total Knee Arthroplasty: A Systematic Review",
                    source = "Journal of Bone and Joint Surgery",
                    dateOrYear = "2023",
                    summary = "Meta-analysis of 1,200 patients shows that robotic-assisted total knee arthroplasty results in significantly more precise component positioning and fewer outlier alignments compared to manual techniques, though long-term functional scores were similar.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            "obgyn" -> listOf(
                FeedItem(
                    id = "mock_sch_ob_1",
                    title = "Intrapartum Uterine Activity and Neonatal Acid-Base Balance: A Prospective Cohort Study",
                    source = "Obstetrics & Gynecology",
                    dateOrYear = "2024",
                    summary = "Cohort study of 500 nulliparous women shows that a high frequency of contractions (tachysystole) in the second stage of labor is strongly correlated with a decrease in umbilical artery pH, highlighting the need for active titration of oxytocin.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_ob_2",
                    title = "Progesterone for the Prevention of Preterm Birth in Twin Gestations with Short Cervix",
                    source = "American Journal of Obstetrics and Gynecology",
                    dateOrYear = "2024",
                    summary = "Individual participant data meta-analysis confirms that vaginal progesterone administration in asymptomatic twin gestations with a mid-trimester cervical length <= 25 mm significantly reduces the risk of preterm birth before 33 weeks.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            "anesthesia" -> listOf(
                FeedItem(
                    id = "mock_sch_ane_1",
                    title = "Target-Controlled Infusion vs. Manual Infusion of Propofol in Pediatric Anesthesia",
                    source = "Anesthesia & Analgesia",
                    dateOrYear = "2024",
                    summary = "Randomized study of 200 pediatric patients indicates that target-controlled infusion of propofol provides significantly more stable hemodynamics and a faster emergence profile compared to manual titration schemes.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_ane_2",
                    title = "Postoperative Nausea and Vomiting: Efficacy of Combined 5-HT3 and NK1 Receptor Antagonists",
                    source = "British Journal of Anaesthesia",
                    dateOrYear = "2024",
                    summary = "Phase 4 trial demonstrates that dual prophylaxis with ondansetron and aprepitant provides superior prevention of postoperative nausea and vomiting compared to single-agent therapy in patients undergoing high-risk laparoscopic surgeries.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            else -> emptyList()
        }
    }
}
