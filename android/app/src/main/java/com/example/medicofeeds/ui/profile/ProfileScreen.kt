package com.example.medicofeeds.ui.profile

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Launch
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.medicofeeds.data.DataRepository
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.data.model.FeedItem
import com.example.medicofeeds.data.model.BookmarkTag
import com.example.medicofeeds.data.model.BookmarkedItem
import com.example.medicofeeds.theme.*
import com.example.medicofeeds.ui.feed.InAppBrowser
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    repository: DataRepository,
    onSignOut: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val userProfileManager = remember { UserProfileManager.getInstance(context) }
    
    val userLevel = remember { userProfileManager.getUserLevel() ?: "MBBS Student" }
    val userSpecialization = remember { userProfileManager.getSpecialization() ?: "General" }
    val userEmail = remember { FirebaseAuth.getInstance().currentUser?.email ?: "physician@medguide.ai" }
    
    var bookmarkedItems by remember { mutableStateOf<List<BookmarkedItem>>(emptyList()) }
    var selectedFilterTag by remember { mutableStateOf<BookmarkTag?>(null) }
    var alertPreferences by remember { mutableStateOf<Map<String, Boolean>>(emptyMap()) }
    var showAlertSettings by remember { mutableStateOf(false) }
    var activeViewUrl by remember { mutableStateOf<String?>(null) }
    
    // Load data on launch
    LaunchedEffect(Unit) {
        bookmarkedItems = repository.getBookmarkedArticles()
        val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
        alertPreferences = repository.getAlertPreferences(userId)
    }

    val filteredItems = remember(bookmarkedItems, selectedFilterTag) {
        if (selectedFilterTag == null) {
            bookmarkedItems
        } else {
            bookmarkedItems.filter { it.tags.contains(selectedFilterTag) }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkCanvas)
            .padding(16.dp)
    ) {
        // --- Profile Header Card ---
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(20.dp))
                .background(CardBg)
                .border(0.5.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(20.dp)),
            colors = CardDefaults.cardColors(containerColor = CardBg)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(56.dp)
                        .clip(RoundedCornerShape(28.dp))
                        .background(SlatePrimary.copy(alpha = 0.15f)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = "Profile",
                        tint = SlatePrimary,
                        modifier = Modifier.size(32.dp)
                    )
                }
                
                Spacer(modifier = Modifier.width(16.dp))
                
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = userEmail,
                        color = TextWhite,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Status: $userLevel" + if (userSpecialization != "General" && userSpecialization.isNotEmpty()) " ($userSpecialization)" else "",
                        color = SlatePrimary,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                
                IconButton(onClick = onSignOut) {
                    Icon(
                        imageVector = Icons.Default.ExitToApp,
                        contentDescription = "Sign Out",
                        tint = ErrorRed,
                        modifier = Modifier.size(24.dp)
                    )
                }
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))

        // --- Breaking Alert Settings ---
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(CardBg)
                .border(0.5.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(16.dp)),
            colors = CardDefaults.cardColors(containerColor = CardBg)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp)
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { showAlertSettings = !showAlertSettings },
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "🔔 Breaking Alert Settings",
                        color = TextWhite,
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp
                    )
                    Text(
                        text = if (showAlertSettings) "COLLAPSE" else "EXPAND",
                        color = SlatePrimary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }

                if (showAlertSettings) {
                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "Enable push notifications for critical guideline updates from these organizations:",
                        color = TextMuted,
                        fontSize = 12.sp,
                        modifier = Modifier.padding(bottom = 12.dp)
                    )

                    val sourcesList = listOf("WHO SEARO", "DOHFW", "DGHS", "AAP", "KDIGO", "ACOG")
                    sourcesList.chunked(2).forEach { pair ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                            horizontalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            pair.forEach { source ->
                                val isEnabled = alertPreferences[source] ?: true
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = source,
                                        color = TextWhite.copy(alpha = 0.9f),
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Medium
                                    )
                                    Switch(
                                        checked = isEnabled,
                                        onCheckedChange = { checked ->
                                            val updated = alertPreferences.toMutableMap()
                                            updated[source] = checked
                                            alertPreferences = updated
                                            coroutineScope.launch {
                                                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                                                repository.updateAlertPreferences(userId, updated)
                                            }
                                        },
                                        colors = SwitchDefaults.colors(
                                            checkedThumbColor = Color.Black,
                                            checkedTrackColor = SlatePrimary,
                                            uncheckedThumbColor = TextMuted,
                                            uncheckedTrackColor = Color.White.copy(alpha = 0.1f)
                                        ),
                                        modifier = Modifier.scale(0.85f)
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "YOUR BOOKMARKED FEEDS",
            color = TextWhite,
            fontWeight = FontWeight.Bold,
            fontSize = 14.sp,
            letterSpacing = 1.sp,
            modifier = Modifier.padding(bottom = 12.dp)
        )

        // --- Tag Filter Chips Row ---
        if (bookmarkedItems.isNotEmpty()) {
            LazyRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                item {
                    FilterChip(
                        selected = selectedFilterTag == null,
                        onClick = { selectedFilterTag = null },
                        label = { Text("All") },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = SlatePrimary,
                            selectedLabelColor = Color.Black,
                            containerColor = CardBg,
                            labelColor = TextWhite
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            enabled = true,
                            selected = selectedFilterTag == null,
                            borderColor = Color.White.copy(alpha = 0.15f),
                            selectedBorderColor = SlatePrimary
                        )
                    )
                }
                items(BookmarkTag.entries) { tag ->
                    FilterChip(
                        selected = selectedFilterTag == tag,
                        onClick = { selectedFilterTag = tag },
                        label = { Text(tag.displayName) },
                        colors = FilterChipDefaults.filterChipColors(
                            selectedContainerColor = Color(tag.colorHex),
                            selectedLabelColor = Color.Black,
                            containerColor = CardBg,
                            labelColor = TextWhite
                        ),
                        border = FilterChipDefaults.filterChipBorder(
                            enabled = true,
                            selected = selectedFilterTag == tag,
                            borderColor = Color.White.copy(alpha = 0.15f),
                            selectedBorderColor = Color(tag.colorHex)
                        )
                    )
                }
            }
        }
        
        // --- Bookmarks List ---
        if (filteredItems.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = if (selectedFilterTag == null) {
                        "No bookmarked articles yet.\nBookmark feeds to read them later offline."
                    } else {
                        "No bookmarked articles matching this tag."
                    },
                    color = TextMuted,
                    fontSize = 14.sp,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                items(filteredItems, key = { it.item.id }) { bookmarkedItem ->
                    BookmarkItemCard(
                        bookmarkedItem = bookmarkedItem,
                        onReadClick = { activeViewUrl = bookmarkedItem.item.fullTextUrl },
                        onRemoveClick = {
                            coroutineScope.launch {
                                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                                repository.toggleBookmark(userId, bookmarkedItem.item, false)
                                bookmarkedItems = repository.getBookmarkedArticles()
                            }
                        }
                    )
                }
            }
        }
        
        // --- In-App Reader Web View Dialog ---
        activeViewUrl?.let { url ->
            InAppBrowser(
                url = url,
                onDismiss = { activeViewUrl = null }
            )
        }
    }
}

@Composable
fun BookmarkItemCard(
    bookmarkedItem: BookmarkedItem,
    onReadClick: () -> Unit,
    onRemoveClick: () -> Unit
) {
    val item = bookmarkedItem.item
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(CardBg)
            .border(0.5.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(16.dp))
            .clickable(onClick = onReadClick),
        colors = CardDefaults.cardColors(containerColor = CardBg)
    ) {
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(if (item.isGuideline) SlatePrimary.copy(alpha = 0.12f) else TealSecondary.copy(alpha = 0.12f))
                        .padding(horizontal = 8.dp, vertical = 3.dp)
                ) {
                    Text(
                        text = if (item.isGuideline) "GUIDELINE" else "RESEARCH",
                        color = if (item.isGuideline) SlatePrimary else TealSecondary,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
                
                Text(
                    text = item.dateOrYear,
                    color = TextMuted,
                    fontSize = 11.sp
                )
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = item.title,
                color = TextWhite,
                fontWeight = FontWeight.Bold,
                fontSize = 14.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            
            Spacer(modifier = Modifier.height(4.dp))
            
            Text(
                text = item.source,
                color = SlatePrimary,
                fontSize = 11.sp,
                fontWeight = FontWeight.SemiBold
            )
            
            // --- Bookmark Tags Row ---
            if (bookmarkedItem.tags.isNotEmpty()) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(6.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    bookmarkedItem.tags.forEach { tag ->
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(6.dp))
                                .background(Color(tag.colorHex).copy(alpha = 0.12f))
                                .border(0.5.dp, Color(tag.colorHex).copy(alpha = 0.4f), RoundedCornerShape(6.dp))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = if (tag == BookmarkTag.CUSTOM && !bookmarkedItem.customTag.isNullOrBlank()) bookmarkedItem.customTag else tag.displayName,
                                color = Color(tag.colorHex),
                                fontSize = 9.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(
                    onClick = onRemoveClick,
                    contentPadding = PaddingValues(0.dp)
                ) {
                    Text(
                        text = "Remove",
                        color = ErrorRed,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
                
                Button(
                    onClick = onReadClick,
                    colors = ButtonDefaults.buttonColors(containerColor = SlatePrimary.copy(alpha = 0.15f)),
                    shape = RoundedCornerShape(8.dp),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                    modifier = Modifier.height(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Launch,
                        contentDescription = null,
                        tint = SlatePrimary,
                        modifier = Modifier.size(12.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "Read Full",
                        color = SlatePrimary,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }
    }
}
