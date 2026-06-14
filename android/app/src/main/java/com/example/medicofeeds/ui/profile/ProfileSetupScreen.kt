package com.example.medicofeeds.ui.profile

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.School
import androidx.compose.material.icons.filled.LocalHospital
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.medicofeeds.data.UserProfileManager
import com.example.medicofeeds.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileSetupScreen(
    onComplete: () -> Unit
) {
    val context = LocalContext.current
    val userProfileManager = remember { UserProfileManager.getInstance(context) }
    
    var selectedLevel by remember { mutableStateOf<String?>(null) }
    var selectedSpecialization by remember { mutableStateOf<String?>(null) }
    var isSubmitting by remember { mutableStateOf(false) }

    val mdClinicalSpecializations = listOf(
        "General Medicine", "Pediatrics", "Dermatology", 
        "Psychiatry", "Anaesthesiology", "Radiology", 
        "Respiratory Medicine", "Emergency Medicine", "Family Medicine"
    )

    val msSurgicalSpecializations = listOf(
        "General Surgery", "Ophthalmology", "ENT", 
        "Orthopaedics", "Obstetrics & Gynaecology"
    )

    val mdParaClinicalSpecializations = listOf(
        "Pathology", "Pharmacology", "Microbiology", 
        "Community Medicine", "Forensic Medicine"
    )

    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { 
                    Text(
                        "MEDGUIDE AI", 
                        fontWeight = FontWeight.Bold, 
                        color = SlatePrimary,
                        letterSpacing = 1.5.sp
                    ) 
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = DarkCanvas
                )
            )
        },
        containerColor = DarkCanvas
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .padding(horizontal = 24.dp)
                .verticalScroll(scrollState),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(modifier = Modifier.height(16.dp))
            
            Text(
                text = "Complete Your Profile",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = TextWhite,
                textAlign = TextAlign.Center
            )
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = "Select your medical status to personalize your clinical guidelines, research feeds, and calculator preferences.",
                style = MaterialTheme.typography.bodyMedium,
                color = TextMuted,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(horizontal = 8.dp)
            )

            Spacer(modifier = Modifier.height(32.dp))

            // --- UG / PG Selection Cards ---
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Undergraduate (UG) Card
                Card(
                    modifier = Modifier
                        .weight(1f)
                        .height(130.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .border(
                            width = 2.dp,
                            color = if (selectedLevel == "UG") SlatePrimary else Color.Transparent,
                            shape = RoundedCornerShape(16.dp)
                        )
                        .clickable {
                            selectedLevel = "UG"
                            selectedSpecialization = null
                        },
                    colors = CardDefaults.cardColors(
                        containerColor = if (selectedLevel == "UG") CardBg.copy(alpha = 0.8f) else CardBg
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = Icons.Default.School,
                            contentDescription = "UG",
                            tint = if (selectedLevel == "UG") SlatePrimary else TealSecondary,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "Undergraduate\n(MBBS Student)",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = TextWhite,
                            textAlign = TextAlign.Center,
                            lineHeight = 16.sp
                        )
                    }
                }

                // Postgraduate (PG) Card
                Card(
                    modifier = Modifier
                        .weight(1f)
                        .height(130.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .border(
                            width = 2.dp,
                            color = if (selectedLevel == "PG") SlatePrimary else Color.Transparent,
                            shape = RoundedCornerShape(16.dp)
                        )
                        .clickable {
                            selectedLevel = "PG"
                        },
                    colors = CardDefaults.cardColors(
                        containerColor = if (selectedLevel == "PG") CardBg.copy(alpha = 0.8f) else CardBg
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.Center,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            imageVector = Icons.Default.LocalHospital,
                            contentDescription = "PG",
                            tint = if (selectedLevel == "PG") SlatePrimary else TealSecondary,
                            modifier = Modifier.size(32.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "Postgraduate\n(MD/MS/Resident)",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = TextWhite,
                            textAlign = TextAlign.Center,
                            lineHeight = 16.sp
                        )
                    }
                }
            }

            // --- Specialization Selector (Only for PG) ---
            if (selectedLevel == "PG") {
                Spacer(modifier = Modifier.height(32.dp))
                
                Text(
                    text = "Select Specialization",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = SlatePrimary,
                    modifier = Modifier.align(Alignment.Start)
                )
                
                Spacer(modifier = Modifier.height(12.dp))

                // Section 1: MD (Clinical)
                SpecializationGroupSection(
                    title = "MD (Clinical)",
                    options = mdClinicalSpecializations,
                    selectedOption = selectedSpecialization,
                    onSelect = { selectedSpecialization = it }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Section 2: MS (Surgical)
                SpecializationGroupSection(
                    title = "MS (Surgical)",
                    options = msSurgicalSpecializations,
                    selectedOption = selectedSpecialization,
                    onSelect = { selectedSpecialization = it }
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Section 3: MD (Para-Clinical)
                SpecializationGroupSection(
                    title = "MD (Para-Clinical)",
                    options = mdParaClinicalSpecializations,
                    selectedOption = selectedSpecialization,
                    onSelect = { selectedSpecialization = it }
                )
            }

            Spacer(modifier = Modifier.height(40.dp))

            // --- Submit Button ---
            val isButtonEnabled = selectedLevel == "UG" || (selectedLevel == "PG" && selectedSpecialization != null)
            
            Button(
                onClick = {
                    if (selectedLevel == null) return@Button
                    isSubmitting = true
                    
                    userProfileManager.saveProfile(
                        level = selectedLevel!!,
                        specialization = selectedSpecialization
                    ) { success ->
                        isSubmitting = false
                        if (success) {
                            onComplete()
                        } else {
                            Toast.makeText(context, "Saved profile locally. Sync to cloud will retry when online.", Toast.LENGTH_SHORT).show()
                            onComplete() // Proceed anyway using local storage
                        }
                    }
                },
                enabled = isButtonEnabled && !isSubmitting,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(26.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = SlatePrimary,
                    disabledContainerColor = CardBg
                )
            ) {
                if (isSubmitting) {
                    CircularProgressIndicator(color = DarkCanvas, modifier = Modifier.size(24.dp))
                } else {
                    Text(
                        text = "Complete Setup",
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp,
                        color = if (isButtonEnabled) DarkCanvas else TextMuted
                    )
                }
            }

            Spacer(modifier = Modifier.height(48.dp))
        }
    }
}

@Composable
fun SpecializationGroupSection(
    title: String,
    options: List<String>,
    selectedOption: String?,
    onSelect: (String) -> Unit
) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Text(
            text = title,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = TextMuted,
            modifier = Modifier.padding(bottom = 8.dp)
        )

        // Wrap flow of options
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(CardBg)
                .padding(8.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            options.chunked(2).forEach { rowOptions ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    rowOptions.forEach { option ->
                        val isSelected = selectedOption == option
                        Box(
                            modifier = Modifier
                                .weight(1f)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (isSelected) SlatePrimary.copy(alpha = 0.15f) else Color.White.copy(alpha = 0.03f))
                                .border(
                                    width = 1.dp,
                                    color = if (isSelected) SlatePrimary else Color.Transparent,
                                    shape = RoundedCornerShape(8.dp)
                                )
                                .clickable { onSelect(option) }
                                .padding(horizontal = 12.dp, vertical = 12.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    text = option,
                                    color = if (isSelected) SlatePrimary else TextWhite,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    fontSize = 13.sp,
                                    modifier = Modifier.weight(1f)
                                )
                                if (isSelected) {
                                    Icon(
                                        imageVector = Icons.Default.CheckCircle,
                                        contentDescription = "Selected",
                                        tint = SlatePrimary,
                                        modifier = Modifier.size(16.dp)
                                    )
                                }
                            }
                        }
                    }
                    // If odd number of options, fill the empty slot
                    if (rowOptions.size == 1) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }
        }
    }
}
