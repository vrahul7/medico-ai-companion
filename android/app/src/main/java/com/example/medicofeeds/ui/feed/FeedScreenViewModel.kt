package com.example.medicofeeds.ui.feed

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.medicofeeds.data.DataRepository
import com.example.medicofeeds.data.api.RetrofitClient
import com.example.medicofeeds.data.model.FeedbackRequest
import com.example.medicofeeds.data.model.FeedItem
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

sealed interface FeedUiState {
    object Loading : FeedUiState
    data class Success(val items: List<FeedItem>) : FeedUiState
    data class Error(val message: String) : FeedUiState
}

class FeedScreenViewModel(private val repository: DataRepository) : ViewModel() {
    private val _uiState = MutableStateFlow<FeedUiState>(FeedUiState.Loading)
    val uiState: StateFlow<FeedUiState> = _uiState.asStateFlow()

    private val _currentFeedType = MutableStateFlow("guidelines") // "guidelines" or "academic"
    val currentFeedType: StateFlow<String> = _currentFeedType.asStateFlow()

    private val _currentTopic = MutableStateFlow("pediatrics")
    val currentTopic: StateFlow<String> = _currentTopic.asStateFlow()

    private val _bookmarkedIds = MutableStateFlow<Set<String>>(emptySet())
    val bookmarkedIds: StateFlow<Set<String>> = _bookmarkedIds.asStateFlow()

    private val _readIds = MutableStateFlow<Set<String>>(emptySet())
    val readIds: StateFlow<Set<String>> = _readIds.asStateFlow()

    private var guidelinesPage = 1
    private var academicPage = 1

    private val guidelinesList = mutableListOf<FeedItem>()
    private val academicList = mutableListOf<FeedItem>()

    init {
        loadBookmarks()
    }

    fun setFeedTypeAndTopic(type: String, topic: String) {
        val typeChanged = _currentFeedType.value != type
        val topicChanged = _currentTopic.value != topic
        val isEmpty = if (type == "guidelines") guidelinesList.isEmpty() else academicList.isEmpty()
        
        if (typeChanged || topicChanged || isEmpty || _uiState.value is FeedUiState.Loading) {
            _currentFeedType.value = type
            _currentTopic.value = topic
            loadFeed(reset = true)
        }
    }


    fun loadBookmarks() {
        viewModelScope.launch {
            try {
                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                val ids = repository.getBookmarks(userId)
                _bookmarkedIds.value = ids.toSet()
            } catch (e: Exception) {
                // Fail silently
            }
        }
    }

    fun toggleBookmark(item: FeedItem) {
        viewModelScope.launch {
            try {
                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                val isCurrentlyBookmarked = _bookmarkedIds.value.contains(item.id)
                val newBookmarkedState = !isCurrentlyBookmarked
                
                repository.toggleBookmark(userId, item, newBookmarkedState)
                
                _bookmarkedIds.value = if (newBookmarkedState) {
                    _bookmarkedIds.value + item.id
                } else {
                    _bookmarkedIds.value - item.id
                }
            } catch (e: Exception) {
                // Fail silently
            }
        }
    }

    fun markFeedAsRead(itemId: String) {
        if (_readIds.value.contains(itemId)) return
        _readIds.value = _readIds.value + itemId
        
        val currentState = _uiState.value
        if (currentState is FeedUiState.Success) {
            _uiState.value = FeedUiState.Success(currentState.items.filter { it.id != itemId })
        }
        
        viewModelScope.launch {
            try {
                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                repository.markAsRead(userId, itemId)
            } catch (e: Exception) {
                // Fail silently
            }
        }
    }

    fun loadFeed(reset: Boolean = false) {
        viewModelScope.launch {
            if (reset) {
                _uiState.value = FeedUiState.Loading
            }
            try {
                if (_currentFeedType.value == "guidelines") {
                    if (reset) {
                        guidelinesPage = 1
                        guidelinesList.clear()
                    }
                    val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                    val items = repository.getGuidelinesFeed(guidelinesPage, userId)
                    val existingIds = guidelinesList.map { it.id }.toSet()
                    val uniqueNewItems = items.filter { it.id !in existingIds && it.id !in _readIds.value }
                    guidelinesList.addAll(uniqueNewItems)
                    _uiState.value = FeedUiState.Success(guidelinesList.filter { it.id !in _readIds.value })
                } else {
                    if (reset) {
                        academicPage = 1
                        academicList.clear()
                    }
                    val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                    val items = repository.getScholarlyFeed(academicPage, _currentTopic.value, userId)
                    val existingIds = academicList.map { it.id }.toSet()
                    val uniqueNewItems = items.filter { it.id !in existingIds && it.id !in _readIds.value }
                    academicList.addAll(uniqueNewItems)
                    _uiState.value = FeedUiState.Success(academicList.filter { it.id !in _readIds.value })
                }
            } catch (e: Exception) {
                _uiState.value = FeedUiState.Error(e.message ?: "Failed to fetch clinical feeds")
            }
        }
    }

    fun loadNextPage() {
        if (_currentFeedType.value == "guidelines") {
            guidelinesPage++
        } else {
            academicPage++
        }
        loadFeed(reset = false)
    }

    fun submitFeedback(itemId: String, rating: String, comment: String? = null) {
        viewModelScope.launch {
            try {
                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                RetrofitClient.apiService.submitFeedback(
                    FeedbackRequest(
                        user_id = userId,
                        item_id = itemId,
                        rating = rating,
                        comment = comment
                    )
                )
            } catch (e: Exception) {
                // Fail silently in UI or log in analytics
            }
        }
    }
}
