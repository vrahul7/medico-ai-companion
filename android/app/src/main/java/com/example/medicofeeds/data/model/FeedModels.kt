package com.example.medicofeeds.data.model

import kotlinx.serialization.Serializable

@Serializable
data class ResearchArticle(
    val pmid: String,
    val title: String? = null,
    val journal: String? = null,
    val year: String? = null,
    val authors: String? = null,
    val summary: String? = null,
    val abstract: String? = null,
    val pubmed_url: String? = null,
    val pdf_url: String? = null,
    val clinical_digest: String? = null
)

@Serializable
data class ScholarlyResponse(
    val articles: List<ResearchArticle>? = null,
    val page: Int,
    val total_found: Int,
    val has_more: Boolean
)

@Serializable
data class RSSItem(
    val title: String? = null,
    val link: String? = null,
    val published: String? = null,
    val summary: String? = null,
    val source: String? = null,
    val pdf_url: String? = null,
    val clinical_digest: String? = null
)

@Serializable
data class GuidelinesResponse(
    val guidelines: List<RSSItem>? = null
)

@Serializable
data class FeedbackRequest(
    val user_id: String,
    val item_id: String,
    val rating: String,
    val comment: String? = null
)

@Serializable
data class FeedbackResponse(
    val status: String? = null,
    val message: String? = null
)

@Serializable
data class ReadRequest(
    val user_id: String,
    val item_id: String
)

@Serializable
data class BookmarkRequest(
    val user_id: String,
    val item_id: String,
    val bookmarked: Boolean,
    val tags: List<String>? = null
)

@Serializable
data class BookmarksResponse(
    val bookmarked_ids: List<String>
)

data class FeedItem(
    val id: String,
    val title: String,
    val source: String,
    val dateOrYear: String,
    val summary: String,
    val clinicalDigest: String,
    val fullTextUrl: String,
    val pdfUrl: String? = null,
    val isGuideline: Boolean
)

// ── Smart Bookmarks with Tags ──

enum class BookmarkTag(val displayName: String, val colorHex: Long) {
    CARDIOLOGY("Cardiology", 0xFFE53935),
    PEDIATRICS("Pediatrics", 0xFF43A047),
    ICU_PROTOCOL("ICU Protocol", 0xFFFF6F00),
    BOARD_PREP("Board Prep", 0xFF1E88E5),
    EMERGENCY("Emergency", 0xFFD32F2F),
    OBGYN("OB/GYN", 0xFFAD1457),
    SURGERY("Surgery", 0xFF6D4C41),
    DERMATOLOGY("Dermatology", 0xFF8E24AA),
    RADIOLOGY("Radiology", 0xFF00897B),
    ORTHOPEDICS("Orthopedics", 0xFF5C6BC0),
    PSYCHIATRY("Psychiatry", 0xFF7B1FA2),
    PHARMACOLOGY("Pharmacology", 0xFF00ACC1),
    CUSTOM("Custom", 0xFF757575);

    companion object {
        fun fromString(name: String): BookmarkTag? {
            return entries.find { it.name.equals(name, ignoreCase = true) || it.displayName.equals(name, ignoreCase = true) }
        }
    }
}

data class BookmarkedItem(
    val item: FeedItem,
    val tags: Set<BookmarkTag> = emptySet(),
    val customTag: String? = null,
    val bookmarkedAt: Long = System.currentTimeMillis()
)

// ── Breaking Guideline Alerts ──

@Serializable
data class DeviceTokenRequest(
    val user_id: String,
    val fcm_token: String
)

@Serializable
data class AlertPreferences(
    val user_id: String,
    val sources: Map<String, Boolean> = mapOf(
        "WHO SEARO" to true,
        "DOHFW" to true,
        "DGHS" to true,
        "AAP" to true,
        "KDIGO" to true,
        "ACOG" to true
    )
)

@Serializable
data class BookmarkTagUpdateRequest(
    val user_id: String,
    val item_id: String,
    val tags: List<String>
)
