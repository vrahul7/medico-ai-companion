package com.example.medicofeeds.ui.calculator

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Calculate
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.medicofeeds.data.calculators.Calculator
import com.example.medicofeeds.data.calculators.CalculatorResult
import com.example.medicofeeds.data.calculators.InputType
import com.example.medicofeeds.data.calculators.MedicalCalculators
import com.example.medicofeeds.theme.*

@Composable
fun CalculatorScreen() {
    var selectedCalculatorId by remember { mutableStateOf<String?>(null) }

    if (selectedCalculatorId == null) {
        CalculatorListScreen(onSelect = { selectedCalculatorId = it })
    } else {
        val calculator = remember(selectedCalculatorId) { MedicalCalculators.getById(selectedCalculatorId!!) }
        if (calculator != null) {
            BackHandler {
                selectedCalculatorId = null
            }
            CalculatorDetailScreen(
                calculator = calculator,
                onBack = { selectedCalculatorId = null }
            )
        } else {
            selectedCalculatorId = null
        }
    }
}

@Composable
fun CalculatorListScreen(onSelect: (String) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkCanvas)
            .padding(16.dp)
    ) {
        Text(
            text = "Clinical Tools & Calculators",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Bold,
            color = TextWhite,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        Text(
            text = "Accurate, deterministic calculators for clinical decision support.",
            style = MaterialTheme.typography.bodyMedium,
            color = TextMuted,
            modifier = Modifier.padding(bottom = 16.dp)
        )

        LazyVerticalGrid(
            columns = GridCells.Fixed(2),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            modifier = Modifier.fillMaxSize()
        ) {
            items(MedicalCalculators.list) { calc ->
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .clickable { onSelect(calc.id) },
                    colors = CardDefaults.cardColors(containerColor = CardBg),
                    border = BorderStroke(0.5.dp, Color.White.copy(alpha = 0.05f))
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.SpaceBetween
                    ) {
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(TealSecondary.copy(alpha = 0.15f))
                                .padding(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Calculate,
                                contentDescription = null,
                                tint = TealSecondary,
                                modifier = Modifier.size(20.dp)
                            )
                        }

                        Column {
                            Text(
                                text = calc.name,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = TextWhite,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                                lineHeight = 16.sp
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = calc.description,
                                style = MaterialTheme.typography.bodySmall,
                                color = TextMuted,
                                fontSize = 10.sp,
                                maxLines = 2,
                                overflow = TextOverflow.Ellipsis,
                                lineHeight = 12.sp
                            )
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CalculatorDetailScreen(
    calculator: Calculator,
    onBack: () -> Unit
) {
    // Map to hold state values for each input field
    val inputValues = remember(calculator.id) {
        val initialMap = mutableStateMapOf<String, String>()
        calculator.inputs.forEach { input ->
            initialMap[input.id] = input.defaultValue
        }
        initialMap
    }

    var calcResult by remember(calculator.id) { mutableStateOf<CalculatorResult?>(null) }
    val scrollState = rememberScrollState()

    // Run calculation once initially if inputs are present
    LaunchedEffect(calculator.id) {
        calcResult = calculator.calculate(inputValues.toMap())
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkCanvas)
    ) {
        // --- Header Row ---
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 8.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.Default.ArrowBack,
                    contentDescription = "Back",
                    tint = SlatePrimary
                )
            }
            Text(
                text = calculator.name,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                color = TextWhite,
                modifier = Modifier.padding(start = 8.dp)
            )
        }

        Divider(color = Color.White.copy(alpha = 0.05f))

        // --- Scrollable Form & Results ---
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(scrollState)
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = calculator.description,
                style = MaterialTheme.typography.bodyMedium,
                color = TextMuted,
                modifier = Modifier.fillMaxWidth().padding(bottom = 20.dp)
            )

            // --- Form Input Fields ---
            calculator.inputs.forEach { input ->
                Spacer(modifier = Modifier.height(12.dp))
                
                when (val inputType = input.type) {
                    is InputType.Number -> {
                        OutlinedTextField(
                            value = inputValues[input.id] ?: "",
                            onValueChange = { newValue ->
                                inputValues[input.id] = newValue
                                // Real-time calculation on change
                                calcResult = calculator.calculate(inputValues.toMap())
                            },
                            label = { Text(input.name) },
                            trailingIcon = {
                                if (input.unit.isNotEmpty()) {
                                    Text(input.unit, color = TextMuted, fontSize = 12.sp, modifier = Modifier.padding(end = 12.dp))
                                }
                            },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            modifier = Modifier.fillMaxWidth(),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = SlatePrimary,
                                unfocusedBorderColor = Color.White.copy(alpha = 0.15f),
                                focusedLabelColor = SlatePrimary,
                                unfocusedLabelColor = TextMuted,
                                focusedTextColor = Color.White,
                                unfocusedTextColor = Color.White
                            )
                        )
                    }
                    is InputType.Choice -> {
                        Column(modifier = Modifier.fillMaxWidth()) {
                            Text(
                                text = input.name,
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.Bold,
                                color = TextMuted,
                                modifier = Modifier.padding(bottom = 6.dp, start = 4.dp)
                            )
                            
                            // Visual Chips selection for choices
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                inputType.options.forEach { option ->
                                    val isSelected = inputValues[input.id] == option
                                    Box(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clip(RoundedCornerShape(8.dp))
                                            .background(if (isSelected) TealSecondary.copy(alpha = 0.15f) else CardBg)
                                            .border(
                                                width = 1.dp,
                                                color = if (isSelected) TealSecondary else Color.Transparent,
                                                shape = RoundedCornerShape(8.dp)
                                            )
                                            .clickable {
                                                inputValues[input.id] = option
                                                calcResult = calculator.calculate(inputValues.toMap())
                                            }
                                            .padding(vertical = 10.dp, horizontal = 4.dp),
                                        contentAlignment = Alignment.Center
                                    ) {
                                        Text(
                                            text = option,
                                            color = if (isSelected) SlatePrimary else TextWhite,
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                            fontSize = 11.sp,
                                            textAlign = TextAlign.Center,
                                            maxLines = 2,
                                            lineHeight = 12.sp
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(28.dp))

            // --- Result Card ---
            calcResult?.let { result ->
                val cardColor = when (result.status) {
                    "normal" -> Color(0xFF10B981) // Green
                    "warning" -> Color(0xFFF59E0B) // Amber
                    "danger" -> Color(0xFFEF4444) // Red
                    else -> TealSecondary
                }

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(20.dp))
                        .border(1.dp, cardColor.copy(alpha = 0.3f), RoundedCornerShape(20.dp)),
                    colors = CardDefaults.cardColors(
                        containerColor = cardColor.copy(alpha = 0.08f)
                    )
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(
                            text = "RESULT",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = cardColor,
                            letterSpacing = 1.sp
                        )
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = result.value,
                            fontSize = 32.sp,
                            fontWeight = FontWeight.ExtraBold,
                            color = TextWhite
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = result.interpretation,
                            fontSize = 13.sp,
                            color = TextWhite.copy(alpha = 0.85f),
                            textAlign = TextAlign.Center,
                            lineHeight = 18.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}
