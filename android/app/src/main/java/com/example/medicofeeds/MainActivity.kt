package com.example.medicofeeds

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.example.medicofeeds.theme.MedGuideAITheme
import com.google.firebase.FirebaseApp
import com.google.firebase.crashlytics.FirebaseCrashlytics

class MainActivity : ComponentActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)

    // Explicitly initialize Firebase on startup
    FirebaseApp.initializeApp(this)

    // Set custom diagnostics logging for Firebase Crashlytics
    FirebaseCrashlytics.getInstance().setCustomKey("app_launch", "successful")

    enableEdgeToEdge()
    setContent {
      MedGuideAITheme {
        Surface(
          modifier = Modifier.fillMaxSize(),
          color = MaterialTheme.colorScheme.background
        ) {
          MainNavigation()
        }
      }
    }
  }
}
