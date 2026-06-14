package com.example.medicofeeds.data

import android.content.Context
import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.firestore.FirebaseFirestore

class UserProfileManager private constructor(context: Context) {

    private val sharedPreferences = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    companion object {
        private const val PREFS_NAME = "medico_user_prefs"
        private const val KEY_LEVEL = "user_level"
        private const val KEY_SPECIALIZATION = "user_specialization"
        private const val TAG = "UserProfileManager"

        @Volatile
        private var INSTANCE: UserProfileManager? = null

        fun getInstance(context: Context): UserProfileManager {
            return INSTANCE ?: synchronized(this) {
                val instance = UserProfileManager(context.applicationContext)
                INSTANCE = instance
                instance
            }
        }
    }

    fun isProfileComplete(): Boolean {
        val level = getUserLevel()
        if (level == "UG") return true
        if (level == "PG" && !getSpecialization().isNullOrEmpty()) return true
        return false
    }

    fun getUserLevel(): String? {
        return sharedPreferences.getString(KEY_LEVEL, null)
    }

    fun getSpecialization(): String? {
        return sharedPreferences.getString(KEY_SPECIALIZATION, null)
    }

    fun getTopicQuery(): String {
        val level = getUserLevel()
        if (level == "UG") {
            return "general"
        }
        val specialization = getSpecialization()?.lowercase() ?: "general"
        return when (specialization) {
            "general medicine" -> "general_medicine"
            "general surgery" -> "surgery"
            "obstetrics & gynaecology" -> "obgyn"
            "anaesthesiology" -> "anesthesia"
            "radiology" -> "radiology"
            "pediatrics" -> "pediatrics"
            "dermatology" -> "dermatology"
            "psychiatry" -> "psychiatry"
            "orthopaedics" -> "orthopedics"
            "ophthalmology" -> "ophthalmology"
            "ent" -> "ent"
            else -> specialization.replace(" ", "_")
        }
    }

    fun saveProfile(level: String, specialization: String?, onComplete: (Boolean) -> Unit) {
        // 1. Save Locally
        sharedPreferences.edit().apply {
            putString(KEY_LEVEL, level)
            if (level == "PG" && specialization != null) {
                putString(KEY_SPECIALIZATION, specialization)
            } else {
                remove(KEY_SPECIALIZATION)
            }
            apply()
        }

        // 2. Sync to Firestore if authenticated
        val currentUser = FirebaseAuth.getInstance().currentUser
        if (currentUser != null) {
            val uid = currentUser.uid
            val profileData = hashMapOf(
                "level" to level,
                "specialization" to (specialization ?: ""),
                "updatedAt" to System.currentTimeMillis()
            )

            FirebaseFirestore.getInstance().collection("users")
                .document(uid)
                .set(profileData)
                .addOnSuccessListener {
                    Log.d(TAG, "Profile successfully synced to Firestore for uid: $uid")
                    onComplete(true)
                }
                .addOnFailureListener { e ->
                    Log.e(TAG, "Failed to sync profile to Firestore", e)
                    // We call onComplete(true) because local cache is already updated,
                    // but we pass true/false depending on sync status to let caller know.
                    onComplete(false)
                }
        } else {
            onComplete(true)
        }
    }

    fun syncFromFirestore(onComplete: (Boolean) -> Unit) {
        val currentUser = FirebaseAuth.getInstance().currentUser
        if (currentUser == null) {
            onComplete(false)
            return
        }

        val uid = currentUser.uid
        FirebaseFirestore.getInstance().collection("users")
            .document(uid)
            .get()
            .addOnSuccessListener { document ->
                if (document != null && document.exists()) {
                    val level = document.getString("level")
                    val specialization = document.getString("specialization")

                    if (!level.isNullOrEmpty()) {
                        sharedPreferences.edit().apply {
                            putString(KEY_LEVEL, level)
                            if (level == "PG" && !specialization.isNullOrEmpty()) {
                                putString(KEY_SPECIALIZATION, specialization)
                            } else {
                                remove(KEY_SPECIALIZATION)
                            }
                            apply()
                        }
                        Log.d(TAG, "Profile successfully synced from Firestore for uid: $uid")
                        onComplete(true)
                    } else {
                        onComplete(false)
                    }
                } else {
                    Log.d(TAG, "No profile document exists in Firestore for uid: $uid")
                    onComplete(false)
                }
            }
            .addOnFailureListener { e ->
                Log.e(TAG, "Failed to sync profile from Firestore", e)
                onComplete(false)
            }
    }

    fun clearProfile() {
        sharedPreferences.edit().clear().apply()
    }
}
