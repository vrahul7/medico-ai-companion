package com.example.medicofeeds

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.ui.auth.AuthScreen
import com.example.medicofeeds.ui.profile.ProfileSetupScreen
import com.example.medicofeeds.ui.main.MainScreen
import com.google.firebase.auth.FirebaseAuth

@Composable
fun MainNavigation() {
    val context = LocalContext.current
    val auth = FirebaseAuth.getInstance()
    val userProfileManager = UserProfileManager.getInstance(context)

    // Determine starting route dynamically
    val startRoute = when {
        auth.currentUser == null -> AuthRoute
        !userProfileManager.isProfileComplete() -> ProfileSetupRoute
        else -> MainRoute
    }

    val backStack = rememberNavBackStack(startRoute)

    NavDisplay(
        backStack = backStack,
        onBack = { backStack.removeLastOrNull() },
        entryProvider = entryProvider {
            entry<AuthRoute> {
                AuthScreen(
                    onAuthSuccess = {
                        // After successful login, determine next route
                        if (userProfileManager.isProfileComplete()) {
                            backStack.add(MainRoute)
                        } else {
                            backStack.add(ProfileSetupRoute)
                        }
                    }
                )
            }
            entry<ProfileSetupRoute> {
                ProfileSetupScreen(
                    onComplete = {
                        // Redirect to main after completing setup
                        backStack.add(MainRoute)
                    }
                )
            }
            entry<MainRoute> {
                MainScreen(
                    onSignOut = {
                        // Handle sign out, clear profile cache, and redirect to Auth screen
                        userProfileManager.clearProfile()
                        auth.signOut()
                        backStack.add(AuthRoute)
                    }
                )
            }
        }
    )
}
