package com.example.medicofeeds.ui.auth

import android.content.Context
import android.util.Patterns
import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.credentials.CredentialManager
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import com.example.medicofeeds.theme.*
import kotlinx.coroutines.launch

// Note: To configure Google Sign-In, enable the Google provider in Firebase console, 
// copy the Web Client ID generated there, and paste it here.
private const val WEB_CLIENT_ID = "643391458781-dummyclientid.apps.googleusercontent.com"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AuthScreen(onAuthSuccess: () -> Unit) {
    val auth = FirebaseAuth.getInstance()
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()
    val credentialManager = remember { CredentialManager.create(context) }

    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var isSignUp by remember { mutableStateOf(false) }
    var loading by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    // Validation States
    val isEmailValid = remember(email) { email.isNotEmpty() && Patterns.EMAIL_ADDRESS.matcher(email).matches() }
    val isPasswordValid = remember(password) { password.length >= 6 }
    val isConfirmPasswordMatching = remember(password, confirmPassword) { password == confirmPassword }
    
    val canSubmit = remember(isSignUp, isEmailValid, isPasswordValid, isConfirmPasswordMatching) {
        if (isSignUp) {
            isEmailValid && isPasswordValid && isConfirmPasswordMatching && confirmPassword.isNotEmpty()
        } else {
            isEmailValid && password.isNotEmpty()
        }
    }

    // Google Sign-In Flow
    fun handleGoogleSignIn() {
        coroutineScope.launch {
            loading = true
            errorMessage = null
            try {
                val googleIdOption = GetGoogleIdOption.Builder()
                    .setFilterByAuthorizedAccounts(false)
                    .setServerClientId(WEB_CLIENT_ID)
                    .setAutoSelectEnabled(false)
                    .build()

                val request = GetCredentialRequest.Builder()
                    .addCredentialOption(googleIdOption)
                    .build()

                val result = credentialManager.getCredential(context, request)
                val credential = result.credential

                if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                    val idToken = googleIdTokenCredential.idToken
                    val firebaseCredential = GoogleAuthProvider.getCredential(idToken, null)
                    
                    auth.signInWithCredential(firebaseCredential)
                        .addOnSuccessListener {
                            loading = false
                            onAuthSuccess()
                        }
                        .addOnFailureListener { e ->
                            loading = false
                            errorMessage = e.message ?: "Firebase authentication failed"
                        }
                } else {
                    loading = false
                    errorMessage = "Unexpected credential type returned"
                }
            } catch (e: GetCredentialException) {
                loading = false
                errorMessage = e.message ?: "Google Sign-In canceled or failed"
            } catch (e: Exception) {
                loading = false
                errorMessage = e.localizedMessage ?: "Unknown Google Sign-In error"
            }
        }
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkCanvas),
        contentAlignment = Alignment.Center
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(28.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header Section
            Text(
                text = "🩺 MedGuide AI",
                fontSize = 32.sp,
                fontWeight = FontWeight.Bold,
                color = SlatePrimary,
                modifier = Modifier.padding(bottom = 8.dp)
            )
            Text(
                text = "Clinical Guidelines & Research",
                fontSize = 16.sp,
                color = Color.White.copy(alpha = 0.7f),
                modifier = Modifier.padding(bottom = 36.dp)
            )

            // Dynamic Error Message
            errorMessage?.let {
                Text(
                    text = it,
                    color = MaterialTheme.colorScheme.error,
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(bottom = 16.dp)
                )
            }

            // --- 🔵 Google Sign-In Button ---
            Button(
                onClick = { handleGoogleSignIn() },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(25.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color.White.copy(alpha = 0.08f)
                ),
                enabled = !loading
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.AccountCircle,
                        contentDescription = "Google Icon",
                        tint = SlatePrimary,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "Sign in with Google",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextWhite
                    )
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Divider "OR"
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Divider(modifier = Modifier.weight(1f), color = Color.White.copy(alpha = 0.15f))
                Text(
                    text = "OR",
                    color = TextMuted,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 16.dp)
                )
                Divider(modifier = Modifier.weight(1f), color = Color.White.copy(alpha = 0.15f))
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Email Field
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Physician Email") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                leadingIcon = { Icon(Icons.Default.Email, contentDescription = "Email", tint = TextMuted) },
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = SlatePrimary,
                    unfocusedBorderColor = Color.White.copy(alpha = 0.3f),
                    focusedLabelColor = SlatePrimary,
                    unfocusedLabelColor = Color.White.copy(alpha = 0.5f),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                )
            )

            // Password Field
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text(if (isSignUp) "Choose Password (min 6 chars)" else "Password") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                leadingIcon = { Icon(Icons.Default.Lock, contentDescription = "Password", tint = TextMuted) },
                modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = SlatePrimary,
                    unfocusedBorderColor = Color.White.copy(alpha = 0.3f),
                    focusedLabelColor = SlatePrimary,
                    unfocusedLabelColor = Color.White.copy(alpha = 0.5f),
                    focusedTextColor = Color.White,
                    unfocusedTextColor = Color.White
                )
            )

            // Confirm Password Field (Sign-up mode only)
            if (isSignUp) {
                OutlinedTextField(
                    value = confirmPassword,
                    onValueChange = { confirmPassword = it },
                    label = { Text("Confirm Password") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    leadingIcon = { Icon(Icons.Default.Lock, contentDescription = "Confirm Password", tint = TextMuted) },
                    modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = if (isConfirmPasswordMatching) SlatePrimary else ErrorRed,
                        unfocusedBorderColor = if (isConfirmPasswordMatching) Color.White.copy(alpha = 0.3f) else ErrorRed,
                        focusedLabelColor = if (isConfirmPasswordMatching) SlatePrimary else ErrorRed,
                        unfocusedLabelColor = if (isConfirmPasswordMatching) Color.White.copy(alpha = 0.5f) else ErrorRed,
                        focusedTextColor = Color.White,
                        unfocusedTextColor = Color.White
                    )
                )

                if (confirmPassword.isNotEmpty() && !isConfirmPasswordMatching) {
                    Text(
                        text = "Passwords do not match",
                        color = ErrorRed,
                        fontSize = 12.sp,
                        modifier = Modifier.align(Alignment.Start).padding(bottom = 12.dp, start = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Action Button
            Button(
                onClick = {
                    if (!canSubmit) return@Button

                    // Hardcoded credentials bypass for local testing
                    val inputEmail = email.trim()
                    if (inputEmail.equals("vgrahul7@gmail.com", ignoreCase = true) && password == "123456789") {
                        onAuthSuccess()
                        return@Button
                    }

                    loading = true
                    errorMessage = null

                    if (isSignUp) {
                        auth.createUserWithEmailAndPassword(email.trim(), password)
                            .addOnSuccessListener {
                                loading = false
                                Toast.makeText(context, "Account created successfully!", Toast.LENGTH_SHORT).show()
                                onAuthSuccess()
                            }
                            .addOnFailureListener { e ->
                                loading = false
                                errorMessage = e.message ?: "Registration failed"
                            }
                    } else {
                        auth.signInWithEmailAndPassword(email.trim(), password)
                            .addOnSuccessListener {
                                loading = false
                                onAuthSuccess()
                            }
                            .addOnFailureListener { e ->
                                loading = false
                                errorMessage = e.message ?: "Authentication failed"
                            }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp),
                shape = RoundedCornerShape(25.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = SlatePrimary,
                    disabledContainerColor = CardBg
                ),
                enabled = canSubmit && !loading
            ) {
                if (loading) {
                    CircularProgressIndicator(color = DarkCanvas, modifier = Modifier.size(24.dp))
                } else {
                    Text(
                        text = if (isSignUp) "Register & Sign In" else "Sign In",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (canSubmit) DarkCanvas else TextMuted
                    )
                }
            }

            // Mode Toggle
            TextButton(
                onClick = {
                    isSignUp = !isSignUp
                    errorMessage = null
                    confirmPassword = ""
                },
                modifier = Modifier.padding(top = 8.dp)
            ) {
                Text(
                    text = if (isSignUp) "Already have an account? Sign In" else "Don't have an account? Sign Up",
                    color = Color.White.copy(alpha = 0.6f),
                    fontSize = 14.sp
                )
            }
        }
    }
}
