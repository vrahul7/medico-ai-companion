package com.example.medicofeeds.data.api

import com.example.medicofeeds.data.model.*
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface MedGuideApi {
    @GET("api/research/scholarly")
    suspend fun getScholarlyFeed(
        @Query("page") page: Int,
        @Query("topic") topic: String,
        @Query("user_id") userId: String?
    ): ScholarlyResponse

    @GET("api/research/guidelines")
    suspend fun getGuidelinesFeed(
        @Query("page") page: Int,
        @Query("user_id") userId: String?
    ): GuidelinesResponse

    @POST("api/research/feedback")
    suspend fun submitFeedback(
        @Body request: FeedbackRequest
    ): FeedbackResponse

    @POST("api/research/read")
    suspend fun markAsRead(
        @Body request: ReadRequest
    ): FeedbackResponse

    @POST("api/research/bookmark")
    suspend fun toggleBookmark(
        @Body request: BookmarkRequest
    ): FeedbackResponse

    @GET("api/research/bookmarks")
    suspend fun getBookmarks(
        @Query("user_id") userId: String
    ): BookmarksResponse
}
