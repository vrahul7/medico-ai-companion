package com.example.medicofeeds.data

import android.util.Log
import com.example.medicofeeds.data.api.RetrofitClient
import com.example.medicofeeds.data.model.BookmarkTag
import com.example.medicofeeds.data.model.BookmarkedItem
import com.example.medicofeeds.data.model.FeedItem
import com.example.medicofeeds.data.model.BookmarkTagUpdateRequest
import com.google.firebase.auth.FirebaseAuth
import java.io.IOException

interface DataRepository {
    suspend fun getScholarlyFeed(page: Int, topic: String, userId: String?): List<FeedItem>
    suspend fun getGuidelinesFeed(page: Int, userId: String?): List<FeedItem>
    suspend fun markAsRead(userId: String, itemId: String)
    suspend fun toggleBookmark(userId: String, item: FeedItem, bookmarked: Boolean, tags: Set<BookmarkTag> = emptySet(), customTag: String? = null)
    suspend fun getBookmarks(userId: String): List<String>
    suspend fun getBookmarkedArticles(): List<BookmarkedItem>
    suspend fun getBookmarkedArticlesByTag(tag: BookmarkTag): List<BookmarkedItem>
    suspend fun updateBookmarkTags(userId: String, itemId: String, tags: Set<BookmarkTag>, customTag: String? = null)
    suspend fun registerDeviceToken(userId: String, fcmToken: String)
    suspend fun getAlertPreferences(userId: String): Map<String, Boolean>
    suspend fun updateAlertPreferences(userId: String, preferences: Map<String, Boolean>)
}

class DefaultDataRepository(private val context: android.content.Context) : DataRepository {
    private val gson = com.google.gson.Gson()
    private val sharedPrefs = context.getSharedPreferences("medguide_bookmarks", android.content.Context.MODE_PRIVATE)
    private val itemCache = java.util.concurrent.ConcurrentHashMap<String, FeedItem>()

    // ── BookmarkedItem local storage (with tags) ──

    private fun getLocalBookmarkedItems(): MutableMap<String, BookmarkedItem> {
        val json = sharedPrefs.getString("bookmarked_items_v2", null) ?: run {
            // Migrate from old format if exists
            return migrateOldBookmarks()
        }
        return try {
            val type = object : com.google.gson.reflect.TypeToken<MutableMap<String, BookmarkedItem>>() {}.type
            gson.fromJson(json, type) ?: mutableMapOf()
        } catch (e: Exception) {
            mutableMapOf()
        }
    }

    private fun migrateOldBookmarks(): MutableMap<String, BookmarkedItem> {
        val oldJson = sharedPrefs.getString("bookmarks_map", null) ?: return mutableMapOf()
        return try {
            val type = object : com.google.gson.reflect.TypeToken<MutableMap<String, FeedItem>>() {}.type
            val oldMap: MutableMap<String, FeedItem> = gson.fromJson(oldJson, type) ?: return mutableMapOf()
            val newMap = mutableMapOf<String, BookmarkedItem>()
            for ((id, item) in oldMap) {
                newMap[id] = BookmarkedItem(item = item, tags = emptySet(), bookmarkedAt = System.currentTimeMillis())
            }
            saveLocalBookmarkedItems(newMap)
            newMap
        } catch (e: Exception) {
            mutableMapOf()
        }
    }

    private fun saveLocalBookmarkedItems(map: Map<String, BookmarkedItem>) {
        val json = gson.toJson(map)
        sharedPrefs.edit().putString("bookmarked_items_v2", json).apply()
    }

    override suspend fun getBookmarkedArticles(): List<BookmarkedItem> {
        return getLocalBookmarkedItems().values.toList().sortedByDescending { it.bookmarkedAt }
    }

    override suspend fun getBookmarkedArticlesByTag(tag: BookmarkTag): List<BookmarkedItem> {
        return getLocalBookmarkedItems().values
            .filter { it.tags.contains(tag) }
            .sortedByDescending { it.bookmarkedAt }
    }

    override suspend fun updateBookmarkTags(userId: String, itemId: String, tags: Set<BookmarkTag>, customTag: String?) {
        val items = getLocalBookmarkedItems()
        val existing = items[itemId] ?: return
        items[itemId] = existing.copy(tags = tags, customTag = customTag)
        saveLocalBookmarkedItems(items)

        try {
            RetrofitClient.apiService.updateBookmarkTags(
                BookmarkTagUpdateRequest(
                    user_id = userId,
                    item_id = itemId,
                    tags = tags.map { it.name } + (if (customTag != null) listOf("CUSTOM:$customTag") else emptyList())
                )
            )
        } catch (e: Exception) {
            // Fail silently — local storage is authoritative
        }
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
                    clinicalDigest = it.clinical_digest ?: extractFallbackDigest(it.summary ?: it.title ?: ""),
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
                    clinicalDigest = it.clinical_digest ?: extractFallbackDigest(it.summary ?: it.title ?: ""),
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

    /** Extracts a concise 2-sentence fallback digest when the backend doesn't provide one */
    private fun extractFallbackDigest(text: String): String {
        if (text.isBlank()) return "Clinical significance details pending AI analysis."
        val sentences = text.split(Regex("(?<=[.!?])\\s+")).filter { it.length > 10 }
        return if (sentences.size >= 2) {
            "${sentences[0].trim()} ${sentences[1].trim()}"
        } else {
            sentences.firstOrNull()?.trim() ?: text.take(150).trim()
        }
    }

    override suspend fun markAsRead(userId: String, itemId: String) {
        try {
            RetrofitClient.apiService.markAsRead(com.example.medicofeeds.data.model.ReadRequest(userId, itemId))
        } catch (e: Exception) {
            // Fail silently in offline mode
        }
    }

    override suspend fun toggleBookmark(userId: String, item: FeedItem, bookmarked: Boolean, tags: Set<BookmarkTag>, customTag: String?) {
        try {
            val bookmarkedItems = getLocalBookmarkedItems()
            if (bookmarked) {
                bookmarkedItems[item.id] = BookmarkedItem(
                    item = item,
                    tags = tags,
                    customTag = customTag,
                    bookmarkedAt = System.currentTimeMillis()
                )
            } else {
                bookmarkedItems.remove(item.id)
            }
            saveLocalBookmarkedItems(bookmarkedItems)

            val tagStrings = tags.map { it.name } + (if (customTag != null) listOf("CUSTOM:$customTag") else emptyList())
            RetrofitClient.apiService.toggleBookmark(
                com.example.medicofeeds.data.model.BookmarkRequest(userId, item.id, bookmarked, tagStrings)
            )
        } catch (e: Exception) {
            // Fail silently in offline mode
        }
    }

    override suspend fun getBookmarks(userId: String): List<String> {
        return try {
            RetrofitClient.apiService.getBookmarks(userId).bookmarked_ids
        } catch (e: Exception) {
            getLocalBookmarkedItems().keys.toList()
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
                clinicalDigest = "⚡ Start obesity pharmacotherapy at age 12+. IHBLT begins at age 6 with family-based approach.",
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
                clinicalDigest = "⚡ SGLT2i first-line for CKD + HF/T2DM when eGFR ≥20. Maximize RAS inhibitor dose for albuminuria.",
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
                clinicalDigest = "⚡ MTX remains first-line for RA. Add biologic/JAKi if target not met; taper steroids rapidly.",
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
                clinicalDigest = "⚡ IV artesunate is first-line for severe malaria. Rectal artesunate for pre-referral in children <6y.",
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
                clinicalDigest = "⚡ Low-dose ASA 81mg from 12–28 wk for high-risk preeclampsia. Deliver at 37wk (mild) or 34wk (severe).",
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
                    clinicalDigest = "⚡ Maternal RSVpreF vaccine reduces severe infant RSV illness through 150 days. No safety concerns found.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                ),
                FeedItem(
                    id = "mock_sch_ped_2",
                    title = "Early Peanut Introduction in High-Risk Infants: 5-Year Allergy Outcomes",
                    source = "The Lancet",
                    dateOrYear = "2024",
                    summary = "Follow-up of the LEAP cohort confirms that early introduction of peanut products in infants with severe eczema or egg allergy leads to an 81% reduction in peanut allergy prevalence at age 5 compared to avoidance.",
                    clinicalDigest = "⚡ Early peanut introduction in high-risk infants reduces peanut allergy by 81% at age 5.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
            else -> listOf(
                FeedItem(
                    id = "mock_sch_gen_1",
                    title = "Advances in Clinical Medicine: A Comprehensive Review",
                    source = "The Lancet",
                    dateOrYear = "2024",
                    summary = "Review of recent clinical advances across multiple disciplines.",
                    clinicalDigest = "⚡ Multi-discipline clinical advances review covering latest evidence-based practice updates.",
                    fullTextUrl = "https://pubmed.ncbi.nlm.nih.gov/",
                    isGuideline = false
                )
            )
        }
    }

    override suspend fun registerDeviceToken(userId: String, fcmToken: String) {
        try {
            RetrofitClient.apiService.registerDeviceToken(
                com.example.medicofeeds.data.model.DeviceTokenRequest(userId, fcmToken)
            )
        } catch (e: Exception) {
            Log.e("DefaultDataRepository", "Failed to register FCM token with backend: ${e.message}")
        }
    }

    override suspend fun getAlertPreferences(userId: String): Map<String, Boolean> {
        return try {
            RetrofitClient.apiService.getAlertPreferences(userId).sources
        } catch (e: Exception) {
            Log.e("DefaultDataRepository", "Failed to get alert preferences: ${e.message}")
            mapOf(
                "WHO SEARO" to true,
                "DOHFW" to true,
                "DGHS" to true,
                "AAP" to true,
                "KDIGO" to true,
                "ACOG" to true
            )
        }
    }

    override suspend fun updateAlertPreferences(userId: String, preferences: Map<String, Boolean>) {
        try {
            RetrofitClient.apiService.updateAlertPreferences(
                com.example.medicofeeds.data.model.AlertPreferences(userId, preferences)
            )
        } catch (e: Exception) {
            Log.e("DefaultDataRepository", "Failed to update alert preferences: ${e.message}")
        }
    }
}
