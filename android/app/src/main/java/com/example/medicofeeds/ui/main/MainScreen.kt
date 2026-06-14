package com.example.medicofeeds.ui.main

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.util.Log
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import androidx.core.content.ContextCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.example.medicofeeds.data.DefaultDataRepository
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.ui.feed.FeedScreen
import com.example.medicofeeds.ui.feed.FeedScreenViewModel
import com.example.medicofeeds.ui.calculator.CalculatorScreen
import com.example.medicofeeds.ui.profile.ProfileScreen
import com.example.medicofeeds.theme.*
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.launch

private fun registerFCMToken(
    context: android.content.Context,
    repository: DefaultDataRepository,
    scope: kotlinx.coroutines.CoroutineScope
) {
    try {
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                Log.w("FCM", "Fetching FCM registration token failed", task.exception)
                return@addOnCompleteListener
            }
            val token = task.result ?: return@addOnCompleteListener
            Log.d("FCM", "FCM token fetched: $token")
            scope.launch {
                try {
                    val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                    repository.registerDeviceToken(userId, token)
                } catch (e: Exception) {
                    Log.e("FCM", "Failed to register device token with backend: ${e.message}")
                }
            }
        }
    } catch (e: Exception) {
        Log.e("FCM", "FirebaseMessaging failed to initialize: ${e.message}")
    }
}

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
    val scope = rememberCoroutineScope()

    val launcher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            registerFCMToken(context, repository, scope)
        }
    }

    LaunchedEffect(Unit) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            val permission = Manifest.permission.POST_NOTIFICATIONS
            if (ContextCompat.checkSelfPermission(context, permission) != PackageManager.PERMISSION_GRANTED) {
                launcher.launch(permission)
            } else {
                registerFCMToken(context, repository, scope)
            }
        } else {
            registerFCMToken(context, repository, scope)
        }
    }

    Scaffold(
        bottomBar = {
            NavigationBar(
                containerColor = CardBg,
                tonalElevation = 8.dp
            ) {
                NavigationBarItem(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    icon = { Icon(Icons.Default.ListAlt, contentDescription = "Guidelines", modifier = Modifier.size(24.dp)) },
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
                    icon = { Icon(Icons.Default.Feed, contentDescription = "Feeds", modifier = Modifier.size(24.dp)) },
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
                    icon = { Icon(Icons.Default.Calculate, contentDescription = "Calculators", modifier = Modifier.size(24.dp)) },
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
                    icon = { Icon(Icons.Default.Person, contentDescription = "Profile", modifier = Modifier.size(24.dp)) },
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
                    ProfileScreen(repository = repository, onSignOut = onSignOut)
                }
            }
        }
    }
}
