package com.example.medicofeeds.ui.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Launch
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.medicofeeds.data.DataRepository
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.data.model.FeedItem
import com.example.medicofeeds.theme.*
import com.example.medicofeeds.ui.feed.InAppBrowser
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.launch

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
    
    var bookmarkedArticles by remember { mutableStateOf<List<FeedItem>>(emptyList()) }
    var activeViewUrl by remember { mutableStateOf<String?>(null) }
    
    // Load bookmarked articles on start
    LaunchedEffect(Unit) {
        bookmarkedArticles = repository.getBookmarkedArticles()
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
        
        Spacer(modifier = Modifier.height(24.dp))
        
        Text(
            text = "YOUR BOOKMARKED FEEDS",
            color = TextWhite,
            fontWeight = FontWeight.Bold,
            fontSize = 14.sp,
            letterSpacing = 1.sp,
            modifier = Modifier.padding(bottom = 12.dp)
        )
        
        // --- Bookmarks List ---
        if (bookmarkedArticles.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "No bookmarked articles yet.\nBookmark feeds to read them later offline.",
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
                items(bookmarkedArticles, key = { it.id }) { item ->
                    BookmarkItemCard(
                        item = item,
                        onReadClick = { activeViewUrl = item.fullTextUrl },
                        onRemoveClick = {
                            coroutineScope.launch {
                                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                                repository.toggleBookmark(userId, item, false)
                                bookmarkedArticles = repository.getBookmarkedArticles()
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
    item: FeedItem,
    onReadClick: () -> Unit,
    onRemoveClick: () -> Unit
) {
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
