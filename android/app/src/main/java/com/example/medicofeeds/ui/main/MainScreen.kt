package com.example.medicofeeds.ui.main

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Calculate
import androidx.compose.material.icons.filled.Feed
import androidx.compose.material.icons.filled.ListAlt
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.medicofeeds.data.DefaultDataRepository
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.ui.feed.FeedScreen
import com.example.medicofeeds.ui.feed.FeedScreenViewModel
import com.example.medicofeeds.ui.calculator.CalculatorScreen
import com.example.medicofeeds.ui.profile.ProfileScreen
import com.example.medicofeeds.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onSignOut: () -> Unit
) {
    val context = LocalContext.current
    val userProfileManager = remember { UserProfileManager.getInstance(context) }
    val repository = remember { DefaultDataRepository(context) }
    
    // Read specialization query from profile manager
    val topicQuery = remember { userProfileManager.getTopicQuery() }
    
    var selectedTab by remember { mutableStateOf(0) }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = when (selectedTab) {
                            0 -> "CLINICAL GUIDELINES"
                            1 -> "RESEARCH FEEDS"
                            2 -> "MEDICAL CALCULATORS"
                            else -> "PROFILE & BOOKMARKS"
                        },
                        fontWeight = FontWeight.Bold,
                        color = SlatePrimary,
                        fontSize = 16.sp,
                        letterSpacing = 1.sp
                    )
                },
                actions = {
                    IconButton(onClick = onSignOut) {
                        Icon(
                            imageVector = Icons.Default.ExitToApp,
                            contentDescription = "Sign Out",
                            tint = SlatePrimary
                        )
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = DarkCanvas
                )
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = CardBg,
                tonalElevation = 8.dp
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.ListAlt, contentDescription = "Guidelines") },
                    label = { Text("Guidelines", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = SlatePrimary,
                        selectedTextColor = SlatePrimary,
                        unselectedIconColor = TextMuted,
                        unselectedTextColor = TextMuted,
                        indicatorColor = GlassOverlay
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    icon = { Icon(Icons.Default.Feed, contentDescription = "Feeds") },
                    label = { Text("Feeds", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = SlatePrimary,
                        selectedTextColor = SlatePrimary,
                        unselectedIconColor = TextMuted,
                        unselectedTextColor = TextMuted,
                        indicatorColor = GlassOverlay
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    icon = { Icon(Icons.Default.Calculate, contentDescription = "Calculators") },
                    label = { Text("Calculators", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = SlatePrimary,
                        selectedTextColor = SlatePrimary,
                        unselectedIconColor = TextMuted,
                        unselectedTextColor = TextMuted,
                        indicatorColor = GlassOverlay
                    )
                )
                NavigationBarItem(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    icon = { Icon(Icons.Default.Person, contentDescription = "Profile") },
                    label = { Text("Profile", fontSize = 11.sp) },
                    colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = SlatePrimary,
                        selectedTextColor = SlatePrimary,
                        unselectedIconColor = TextMuted,
                        unselectedTextColor = TextMuted,
                        indicatorColor = GlassOverlay
                    )
                )
            }
        },
        containerColor = DarkCanvas
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                0 -> {
                    // Guidelines Tab: renders FeedScreen in guidelines mode
                    val feedViewModel: FeedScreenViewModel = viewModel {
                        FeedScreenViewModel(repository)
                    }
                    FeedScreen(
                        viewModel = feedViewModel,
                        feedType = "guidelines",
                        specializationQuery = topicQuery
                    )
                }
                1 -> {
                    // Feeds Tab: renders FeedScreen in academic mode
                    val feedViewModel: FeedScreenViewModel = viewModel {
                        FeedScreenViewModel(repository)
                    }
                    FeedScreen(
                        viewModel = feedViewModel,
                        feedType = "academic",
                        specializationQuery = topicQuery
                    )
                }
                2 -> {
                    // Calculators Tab
                    CalculatorScreen()
                }
                3 -> {
                    // Profile & Bookmarks Tab
                    ProfileScreen(repository = repository)
                }
            }
        }
    }
}
