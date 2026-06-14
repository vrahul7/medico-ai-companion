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
    val pdf_url: String? = null
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
    val pdf_url: String? = null
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
    val bookmarked: Boolean
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
    val fullTextUrl: String,
    val pdfUrl: String? = null,
    val isGuideline: Boolean
)
