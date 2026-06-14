package com.example.medicofeeds.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.example.medicofeeds.MainActivity
import com.example.medicofeeds.R
import com.example.medicofeeds.data.api.RetrofitClient
import com.example.medicofeeds.data.model.DeviceTokenRequest
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * MedicoFCMService handles Firebase Cloud Messaging for Breaking Guideline Alerts.
 * 
 * Push payload structure from backend:
 * {
 *   "title": "New WHO SEARO Guideline",
 *   "body": "IV artesunate is first-line for severe malaria...",
 *   "source": "WHO SEARO",
 *   "link": "https://www.who.int/...",
 *   "type": "breaking_guideline"
 * }
 */
class MedicoFCMService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "MedicoFCM"
        const val CHANNEL_ID = "breaking_guidelines"
        const val CHANNEL_NAME = "Breaking Guidelines"
        const val CHANNEL_DESC = "Notifications for new clinical guidelines from WHO, DOHFW, AAP, and other authorities"
        private var notificationIdCounter = 1000
    }

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d(TAG, "New FCM token received: ${token.take(20)}...")
        registerTokenWithBackend(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        Log.d(TAG, "FCM message received from: ${message.from}")

        // Handle data payload (preferred for control over notification display)
        val data = message.data
        if (data.isNotEmpty()) {
            val title = data["title"] ?: "New Clinical Guideline"
            val body = data["body"] ?: "A new guideline has been published."
            val source = data["source"] ?: "Medical Authority"
            val link = data["link"] ?: ""
            val type = data["type"] ?: "breaking_guideline"

            if (type == "breaking_guideline") {
                showBreakingGuidelineNotification(title, body, source, link)
            }
        }

        // Also handle notification payload (when app is in foreground)
        message.notification?.let { notification ->
            showBreakingGuidelineNotification(
                title = notification.title ?: "New Clinical Guideline",
                body = notification.body ?: "A new guideline has been published.",
                source = message.data["source"] ?: "Medical Authority",
                link = message.data["link"] ?: ""
            )
        }
    }

    private fun showBreakingGuidelineNotification(
        title: String,
        body: String,
        source: String,
        link: String
    ) {
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager

        // Create intent to open the app when notification is tapped
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("notification_link", link)
            putExtra("notification_source", source)
            putExtra("open_tab", "guidelines")
        }

        val pendingIntent = PendingIntent.getActivity(
            this,
            notificationIdCounter,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        // Build CRED-styled notification
        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.medguide_icon)
            .setContentTitle("🔔 $source")
            .setContentText(title)
            .setStyle(
                NotificationCompat.BigTextStyle()
                    .bigText("$title\n\n$body")
                    .setSummaryText("Breaking Guideline Alert")
            )
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setColor(0xFFD4AF37.toInt()) // Gold accent matching app theme
            .build()

        notificationManager.notify(notificationIdCounter++, notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                CHANNEL_NAME,
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = CHANNEL_DESC
                enableLights(true)
                lightColor = 0xFFD4AF37.toInt() // Gold
                enableVibration(true)
            }
            val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun registerTokenWithBackend(token: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val userId = FirebaseAuth.getInstance().currentUser?.uid ?: "anonymous_physician"
                RetrofitClient.apiService.registerDeviceToken(
                    DeviceTokenRequest(user_id = userId, fcm_token = token)
                )
                Log.d(TAG, "FCM token registered with backend successfully")
            } catch (e: Exception) {
                Log.e(TAG, "Failed to register FCM token with backend: ${e.message}")
            }
        }
    }
}
