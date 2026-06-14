package com.example.medicofeeds.ui.feed

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.pager.VerticalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bookmark
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.outlined.BookmarkBorder
import androidx.compose.material.icons.outlined.ThumbDown
import androidx.compose.material.icons.outlined.ThumbUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.google.firebase.analytics.FirebaseAnalytics
import com.example.medicofeeds.data.model.FeedItem
import com.example.medicofeeds.theme.*
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import androidx.compose.ui.viewinterop.AndroidView

@OptIn(ExperimentalFoundationApi::class, ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen(
    viewModel: FeedScreenViewModel,
    feedType: String,
    specializationQuery: String
) {
    val context = LocalContext.current
    val firebaseAnalytics = remember { FirebaseAnalytics.getInstance(context) }
    val uiState by viewModel.uiState.collectAsStateWithLifecycle()
    val bookmarkedIds by viewModel.bookmarkedIds.collectAsStateWithLifecycle()

    var activeViewUrl by remember { mutableStateOf<String?>(null) }

    // Sync Composable input parameters to ViewModel state
    LaunchedEffect(feedType, specializationQuery) {
        viewModel.setFeedTypeAndTopic(feedType, specializationQuery)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkCanvas)
    ) {
        // --- Feed Body ---
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
        ) {
            when (val state = uiState) {
                is FeedUiState.Loading -> {
                    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                        CircularProgressIndicator(color = SlatePrimary)
                    }
                }
                is FeedUiState.Error -> {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(32.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        Text(
                            text = "⚠️ Network Error",
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = ErrorRed,
                            modifier = Modifier.padding(bottom = 8.dp)
                        )
                        Text(
                            text = state.message,
                            fontSize = 14.sp,
                            color = TextMuted,
                            textAlign = TextAlign.Center,
                            modifier = Modifier.padding(bottom = 16.dp)
                        )
                        Button(
                            onClick = { viewModel.loadFeed(reset = true) },
                            colors = ButtonDefaults.buttonColors(containerColor = SlatePrimary)
                        ) {
                            Text("Retry Connections", color = Color.Black)
                        }
                    }
                }
                is FeedUiState.Success -> {
                    val items = state.items
                    if (items.isEmpty()) {
                        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                            Text("No recent feeds available", color = TextMuted)
                        }
                    } else {
                        val pagerState = rememberPagerState(pageCount = { items.size })

                        // Trigger next page fetching
                        LaunchedEffect(pagerState.currentPage) {
                            if (pagerState.currentPage >= items.size - 2) {
                                viewModel.loadNextPage()
                            }
                        }

                        // Track card views in Firebase Analytics
                        LaunchedEffect(pagerState.currentPage) {
                            if (items.isNotEmpty() && pagerState.currentPage < items.size) {
                                val currentItem = items[pagerState.currentPage]
                                val bundle = Bundle().apply {
                                    putString("item_id", currentItem.id)
                                    putString("item_title", currentItem.title)
                                    putString("item_source", currentItem.source)
                                    putBoolean("is_guideline", currentItem.isGuideline)
                                }
                                firebaseAnalytics.logEvent("feed_card_view", bundle)
                            }
                        }

                        // Mark as read after spending 15 seconds on the card
                        LaunchedEffect(pagerState.currentPage) {
                            if (items.isNotEmpty() && pagerState.currentPage < items.size) {
                                val currentItem = items[pagerState.currentPage]
                                kotlinx.coroutines.delay(15000)
                                viewModel.markFeedAsRead(currentItem.id)
                            }
                        }

                        VerticalPager(
                            state = pagerState,
                            modifier = Modifier.fillMaxSize()
                        ) { page ->
                            val item = items[page]
                            val isBookmarked = bookmarkedIds.contains(item.id)
                            FeedCard(
                                item = item,
                                isBookmarked = isBookmarked,
                                onToggleBookmark = { viewModel.toggleBookmark(item) },
                                onSubmitFeedback = { rating ->
                                    viewModel.submitFeedback(item.id, rating)
                                    // Track feedback in Firebase Analytics
                                    val bundle = Bundle().apply {
                                        putString("item_id", item.id)
                                        putString("rating", rating)
                                    }
                                    firebaseAnalytics.logEvent("rate_summary", bundle)
                                },
                                onReadClick = { activeViewUrl = item.fullTextUrl },
                                modifier = Modifier
                                    .fillMaxSize()
                                    .padding(horizontal = 16.dp, vertical = 24.dp)
                            )
                        }
                    }
                }
            }
        }
    }

    // Show in-app reader if a URL is active
    activeViewUrl?.let { url ->
        InAppBrowser(
            url = url,
            onDismiss = { activeViewUrl = null }
        )
    }
}

@Composable
fun FeedCard(
    item: FeedItem,
    isBookmarked: Boolean,
    onToggleBookmark: () -> Unit,
    onSubmitFeedback: (String) -> Unit,
    onReadClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    var feedbackState by remember(item.id) { mutableStateOf<String?>(null) }

    Box(
        modifier = modifier
            .clip(RoundedCornerShape(24.dp))
            .background(
                brush = androidx.compose.ui.graphics.Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF1E293B).copy(alpha = 0.85f),
                        Color(0xFF0F172A).copy(alpha = 0.95f)
                    )
                )
            )
            .border(1.dp, Color.White.copy(alpha = 0.15f), RoundedCornerShape(24.dp))
            .padding(24.dp)
    ) {
        Column(
            modifier = Modifier.fillMaxSize()
        ) {
            // Source & Date Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(8.dp))
                        .background(if (item.isGuideline) SlatePrimary.copy(alpha = 0.15f) else TealSecondary.copy(alpha = 0.15f))
                        .padding(horizontal = 10.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = if (item.isGuideline) "Guideline" else "Research Paper",
                        color = if (item.isGuideline) SlatePrimary else TealSecondary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                Text(
                    text = item.dateOrYear,
                    color = TextMuted,
                    fontSize = 12.sp
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Clinical Journal Context
            Text(
                text = item.source.uppercase(),
                color = SlatePrimary,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            )

            Spacer(modifier = Modifier.height(8.dp))

            // Primary Title
            Text(
                text = item.title,
                color = TextWhite,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                lineHeight = 28.sp
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Divider
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(1.dp)
                    .background(Color.White.copy(alpha = 0.05f))
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Scrollable AI Summary Block
            Column(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.Black.copy(alpha = 0.2f))
                    .border(0.5.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(16.dp))
                    .padding(16.dp)
                    .verticalScroll(rememberScrollState())
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.padding(bottom = 8.dp)
                ) {
                    Text(
                        text = "✨ AI Clinical Summary",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = TealSecondary
                    )
                }
                Text(
                    text = item.summary,
                    color = TextWhite.copy(alpha = 0.9f),
                    fontSize = 15.sp,
                    lineHeight = 24.sp
                )
            }

            // Bottom controls
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 16.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Interactive Feedback Loops
                Row(
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    IconButton(
                        onClick = {
                            feedbackState = "up"
                            onSubmitFeedback("up")
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.ThumbUp,
                            contentDescription = "Helpful",
                            tint = if (feedbackState == "up") TealSecondary else TextMuted
                        )
                    }

                    IconButton(
                        onClick = {
                            feedbackState = "down"
                            onSubmitFeedback("down")
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Outlined.ThumbDown,
                            contentDescription = "Not Helpful",
                            tint = if (feedbackState == "down") ErrorRed else TextMuted
                        )
                    }
                }

                // Action Row
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Bookmark button
                    IconButton(
                        onClick = onToggleBookmark
                    ) {
                        Icon(
                            imageVector = if (isBookmarked) Icons.Default.Bookmark else Icons.Outlined.BookmarkBorder,
                            contentDescription = if (isBookmarked) "Remove Bookmark" else "Bookmark",
                            tint = if (isBookmarked) TealSecondary else TextWhite
                        )
                    }

                    // Share button
                    IconButton(
                        onClick = {
                            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                                type = "text/plain"
                                putExtra(Intent.EXTRA_SUBJECT, item.title)
                                putExtra(Intent.EXTRA_TEXT, "${item.title}\n\nRead more: ${item.fullTextUrl}")
                            }
                            context.startActivity(Intent.createChooser(shareIntent, "Share Clinical Feed"))
                        }
                    ) {
                        Icon(
                            imageVector = Icons.Default.Share,
                            contentDescription = "Share",
                            tint = TextWhite
                        )
                    }

                    // Read More Button
                    Button(
                        onClick = onReadClick,
                        colors = ButtonDefaults.buttonColors(containerColor = SlatePrimary),
                        shape = RoundedCornerShape(12.dp),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.ExitToApp,
                            contentDescription = null,
                            tint = Color.Black,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Read Full",
                            color = Color.Black,
                            fontWeight = FontWeight.Bold,
                            fontSize = 13.sp
                        )
                    }
                }
            }
        }

        // Vertical Swipe guide label
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 4.dp),
            contentAlignment = Alignment.Center
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.KeyboardArrowUp, null, tint = TextMuted.copy(alpha = 0.3f), modifier = Modifier.size(12.dp))
                Text("Swipe up for next", color = TextMuted.copy(alpha = 0.3f), fontSize = 10.sp, modifier = Modifier.padding(start = 2.dp))
            }
        }
    }
}

@Composable
fun InAppBrowser(url: String, onDismiss: () -> Unit) {
    androidx.compose.ui.window.Dialog(
        properties = androidx.compose.ui.window.DialogProperties(
            usePlatformDefaultWidth = false // Make it full screen
        ),
        onDismissRequest = onDismiss
    ) {
        Surface(
            modifier = Modifier.fillMaxSize(),
            color = DarkCanvas
        ) {
            Column(modifier = Modifier.fillMaxSize()) {
                // Custom Toolbar for in-app reader matching aesthetics
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(CardBg)
                        .padding(horizontal = 16.dp, vertical = 12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(
                        text = "CLINICAL READER",
                        fontWeight = FontWeight.Bold,
                        color = SlatePrimary,
                        fontSize = 14.sp,
                        letterSpacing = 1.sp
                    )
                    Text(
                        text = "CLOSE",
                        color = ErrorRed,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp,
                        modifier = Modifier
                            .clickable(onClick = onDismiss)
                            .padding(8.dp)
                    )
                }

                // WebView Container
                AndroidView(
                    factory = { context ->
                        WebView(context).apply {
                            settings.javaScriptEnabled = true
                            settings.domStorageEnabled = true
                            settings.builtInZoomControls = true
                            settings.displayZoomControls = false
                            settings.useWideViewPort = true
                            settings.loadWithOverviewMode = true
                            
                            webViewClient = object : WebViewClient() {
                                override fun shouldOverrideUrlLoading(
                                    view: WebView?,
                                    url: String?
                                ): Boolean {
                                    return false // Load in WebView
                                }
                            }
                            
                            webChromeClient = WebChromeClient()
                        }
                    },
                    update = { webView ->
                        val finalUrl = if (url.endsWith(".pdf", ignoreCase = true) || url.contains("/pdf/") || url.contains("pdf")) {
                            "https://docs.google.com/gview?embedded=true&url=${Uri.encode(url)}"
                        } else {
                            url
                        }
                        webView.loadUrl(finalUrl)
                    },
                    modifier = Modifier.weight(1f).fillMaxWidth()
                )
            }
        }
    }
}

fun Modifier.noRippleClickable(onClick: () -> Unit): Modifier = composed {
    this.clickable(
        interactionSource = remember { MutableInteractionSource() },
        indication = null,
        onClick = onClick
    )
}
