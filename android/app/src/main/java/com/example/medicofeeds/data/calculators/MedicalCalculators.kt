package com.example.medicofeeds.data.calculators

import kotlin.math.sqrt
import kotlin.math.pow
import kotlin.math.min
import kotlin.math.max

sealed class InputType {
    object Number : InputType()
    data class Choice(val options: List<String>) : InputType()
}

data class InputField(
    val id: String,
    val name: String,
    val type: InputType,
    val defaultValue: String = "",
    val unit: String = ""
)

data class CalculatorResult(
    val value: String,
    val interpretation: String,
    val status: String // "normal", "warning", "danger"
)

object MedicalCalculators {

    val list = listOf(
        BmiCalculator,
        BsaCalculator,
        EgfrCalculator,
        CockcroftGaultCalculator,
        QtcCalculator,
        ApgarCalculator,
        GcsCalculator,
        WellsPeCalculator,
        GestationalWeeksCalculator,
        GrowthMonitoringCalculator
    )

    fun getById(id: String): Calculator? {
        return list.find { it.id == id }
    }
}

abstract class Calculator {
    abstract val id: String
    abstract val name: String
    abstract val description: String
    abstract val inputs: List<InputField>
    abstract fun calculate(values: Map<String, String>): CalculatorResult
}

// 1. BMI Calculator
object BmiCalculator : Calculator() {
    override val id = "bmi"
    override val name = "Body Mass Index (BMI)"
    override val description = "Calculates body mass index to classify weight status."
    override val inputs = listOf(
        InputField("weight", "Weight", InputType.Number, "70", "kg"),
        InputField("height", "Height", InputType.Number, "170", "cm")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val weight = values["weight"]?.toDoubleOrNull() ?: return invalidResult()
        val heightCm = values["height"]?.toDoubleOrNull() ?: return invalidResult()
        if (heightCm <= 0 || weight <= 0) return invalidResult()
        
        val heightM = heightCm / 100.0
        val bmi = weight / (heightM * heightM)
        
        val (interpretation, status) = when {
            bmi < 18.5 -> "Underweight" to "warning"
            bmi in 18.5..24.99 -> "Normal weight" to "normal"
            bmi in 25.0..29.99 -> "Overweight" to "warning"
            else -> "Obese" to "danger"
        }
        
        return CalculatorResult(
            value = String.format("%.2f kg/m²", bmi),
            interpretation = interpretation,
            status = status
        )
    }
}

// 2. BSA Calculator
object BsaCalculator : Calculator() {
    override val id = "bsa"
    override val name = "Body Surface Area (BSA)"
    override val description = "Estimates body surface area using Mosteller formula."
    override val inputs = listOf(
        InputField("weight", "Weight", InputType.Number, "70", "kg"),
        InputField("height", "Height", InputType.Number, "170", "cm")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val weight = values["weight"]?.toDoubleOrNull() ?: return invalidResult()
        val height = values["height"]?.toDoubleOrNull() ?: return invalidResult()
        if (height <= 0 || weight <= 0) return invalidResult()
        
        val bsa = sqrt((height * weight) / 3600.0)
        
        return CalculatorResult(
            value = String.format("%.2f m²", bsa),
            interpretation = "Standard physiological range: 1.6 - 1.9 m² (adults)",
            status = "normal"
        )
    }
}

// 3. eGFR (CKD-EPI 2021)
object EgfrCalculator : Calculator() {
    override val id = "egfr"
    override val name = "eGFR (CKD-EPI 2021)"
    override val description = "Estimates glomerular filtration rate without race coefficient."
    override val inputs = listOf(
        InputField("creatinine", "Serum Creatinine", InputType.Number, "1.0", "mg/dL"),
        InputField("age", "Age", InputType.Number, "45", "years"),
        InputField("gender", "Gender", InputType.Choice(listOf("Male", "Female")), "Male")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val scr = values["creatinine"]?.toDoubleOrNull() ?: return invalidResult()
        val age = values["age"]?.toDoubleOrNull() ?: return invalidResult()
        val gender = values["gender"] ?: "Male"
        
        if (scr <= 0 || age <= 0) return invalidResult()
        
        val isFemale = gender.lowercase() == "female"
        val kappa = if (isFemale) 0.7 else 0.9
        val alpha = if (isFemale) -0.241 else -0.302
        val genderMultiplier = if (isFemale) 1.012 else 1.0
        val ageMultiplier = 0.9938.pow(age)
        
        val term1 = min(scr / kappa, 1.0).pow(alpha)
        val term2 = max(scr / kappa, 1.0).pow(-1.200)
        
        val egfr = 142.0 * term1 * term2 * ageMultiplier * genderMultiplier
        
        val (interpretation, status) = when {
            egfr >= 90.0 -> "Stage G1: Normal or high kidney function" to "normal"
            egfr in 60.0..89.9 -> "Stage G2: Mildly decreased kidney function" to "normal"
            egfr in 45.0..59.9 -> "Stage G3a: Mildly to moderately decreased kidney function" to "warning"
            egfr in 30.0..44.9 -> "Stage G3b: Moderately to severely decreased kidney function" to "warning"
            egfr in 15.0..29.9 -> "Stage G4: Severely decreased kidney function" to "danger"
            else -> "Stage G5: Kidney failure (ESRD)" to "danger"
        }
        
        return CalculatorResult(
            value = String.format("%.1f mL/min/1.73m²", egfr),
            interpretation = interpretation,
            status = status
        )
    }
}

// 4. Creatinine Clearance (Cockcroft-Gault)
object CockcroftGaultCalculator : Calculator() {
    override val id = "crcl"
    override val name = "Creatinine Clearance"
    override val description = "Estimates renal function for drug dosage adjustments."
    override val inputs = listOf(
        InputField("creatinine", "Serum Creatinine", InputType.Number, "1.0", "mg/dL"),
        InputField("age", "Age", InputType.Number, "45", "years"),
        InputField("weight", "Weight", InputType.Number, "70", "kg"),
        InputField("gender", "Gender", InputType.Choice(listOf("Male", "Female")), "Male")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val scr = values["creatinine"]?.toDoubleOrNull() ?: return invalidResult()
        val age = values["age"]?.toDoubleOrNull() ?: return invalidResult()
        val weight = values["weight"]?.toDoubleOrNull() ?: return invalidResult()
        val gender = values["gender"] ?: "Male"
        
        if (scr <= 0 || age <= 0 || weight <= 0) return invalidResult()
        
        var crcl = ((140 - age) * weight) / (72 * scr)
        if (gender.lowercase() == "female") {
            crcl *= 0.85
        }
        
        val (interpretation, status) = when {
            crcl >= 90.0 -> "Normal renal clearance" to "normal"
            crcl in 60.0..89.9 -> "Mild renal impairment" to "normal"
            crcl in 30.0..59.9 -> "Moderate renal impairment (dose adjust required)" to "warning"
            crcl in 15.0..29.9 -> "Severe renal impairment" to "danger"
            else -> "Severe renal failure / ESRD" to "danger"
        }
        
        return CalculatorResult(
            value = String.format("%.1f mL/min", crcl),
            interpretation = interpretation,
            status = status
        )
    }
}

// 5. Corrected QT (Bazett)
object QtcCalculator : Calculator() {
    override val id = "qtc"
    override val name = "Corrected QT Interval (Bazett)"
    override val description = "Bazett's formula correction for heart rate variations."
    override val inputs = listOf(
        InputField("qt", "QT Interval", InputType.Number, "400", "ms"),
        InputField("hr", "Heart Rate", InputType.Number, "72", "bpm"),
        InputField("gender", "Gender", InputType.Choice(listOf("Male", "Female")), "Male")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val qt = values["qt"]?.toDoubleOrNull() ?: return invalidResult()
        val hr = values["hr"]?.toDoubleOrNull() ?: return invalidResult()
        val gender = values["gender"] ?: "Male"
        
        if (qt <= 0 || hr <= 0) return invalidResult()
        
        val rrSeconds = 60.0 / hr
        val qtc = qt / sqrt(rrSeconds)
        
        val isFemale = gender.lowercase() == "female"
        val upperLimit = if (isFemale) 460.0 else 450.0
        
        val (interpretation, status) = when {
            qtc > 500.0 -> "Prolonged (>500 ms): Critical risk of Torsades de Pointes" to "danger"
            qtc > upperLimit -> "Prolonged: Borderline risk" to "warning"
            qtc < 350.0 -> "Shortened (<350 ms): Risk of Short QT Syndrome" to "warning"
            else -> "Normal QT interval" to "normal"
        }
        
        return CalculatorResult(
            value = String.format("%.0f ms", qtc),
            interpretation = interpretation,
            status = status
        )
    }
}

// 6. APGAR Score
object ApgarCalculator : Calculator() {
    override val id = "apgar"
    override val name = "APGAR Score"
    override val description = "Neonatal assessment at 1 and 5 minutes post-birth."
    override val inputs = listOf(
        InputField("color", "Appearance (Skin Color)", InputType.Choice(listOf("0: Blue/Pale all over", "1: Blue extremities", "2: Completely pink")), "2: Completely pink"),
        InputField("pulse", "Pulse (Heart Rate)", InputType.Choice(listOf("0: Absent", "1: <100 bpm", "2: >=100 bpm")), "2: >=100 bpm"),
        InputField("grimace", "Grimace (Reflex Irritability)", InputType.Choice(listOf("0: No response", "1: Grimace on suction/slap", "2: Cry/Sneeze/Cough")), "2: Cry/Sneeze/Cough"),
        InputField("activity", "Activity (Muscle Tone)", InputType.Choice(listOf("0: Limp/Flaccid", "1: Some flexion", "2: Active motion")), "2: Active motion"),
        InputField("respiration", "Respiration (Effort)", InputType.Choice(listOf("0: Absent", "1: Weak/Slow/Irregular", "2: Strong cry")), "2: Strong cry")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        var score = 0
        listOf("color", "pulse", "grimace", "activity", "respiration").forEach { key ->
            val value = values[key] ?: return invalidResult()
            // Extract the first character as the integer score (0, 1, or 2)
            val point = value.substringBefore(":").trim().toIntOrNull() ?: return invalidResult()
            score += point
        }

        val (interpretation, status) = when {
            score >= 7 -> "7 - 10: Normal. Baby in good health." to "normal"
            score in 4..6 -> "4 - 6: Moderately abnormal. May need suctioning or oxygen." to "warning"
            else -> "0 - 3: Critically low. Needs immediate resuscitation." to "danger"
        }

        return CalculatorResult(
            value = "$score / 10",
            interpretation = interpretation,
            status = status
        )
    }
}

// 7. Glasgow Coma Scale (GCS)
object GcsCalculator : Calculator() {
    override val id = "gcs"
    override val name = "Glasgow Coma Scale (GCS)"
    override val description = "Scores Level of Consciousness in acute trauma."
    override val inputs = listOf(
        InputField("eye", "Eye Opening", InputType.Choice(listOf("1: None", "2: To pain", "3: To sound", "4: Spontaneous")), "4: Spontaneous"),
        InputField("verbal", "Verbal Response", InputType.Choice(listOf("1: None", "2: Incomprehensible sounds", "3: Inappropriate words", "4: Confused", "5: Oriented")), "5: Oriented"),
        InputField("motor", "Motor Response", InputType.Choice(listOf("1: None", "2: Extension (decerebrate)", "3: Abnormal flexion (decorticate)", "4: Withdrawal from pain", "5: Localizes pain", "6: Obeys commands")), "6: Obeys commands")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        var score = 0
        listOf("eye", "verbal", "motor").forEach { key ->
            val value = values[key] ?: return invalidResult()
            val point = value.substringBefore(":").trim().toIntOrNull() ?: return invalidResult()
            score += point
        }

        val (interpretation, status) = when {
            score >= 13 -> "GCS 13-15: Mild Brain Injury" to "normal"
            score in 9..12 -> "GCS 9-12: Moderate Brain Injury" to "warning"
            else -> "GCS 3-8: Severe Brain Injury (Coma/Intubate)" to "danger"
        }

        return CalculatorResult(
            value = "E${values["eye"]?.first()} V${values["verbal"]?.first()} M${values["motor"]?.first()} (Total: $score)",
            interpretation = interpretation,
            status = status
        )
    }
}

// 8. Wells Score for PE
object WellsPeCalculator : Calculator() {
    override val id = "wellspe"
    override val name = "Wells Criteria for Pulmonary Embolism"
    override val description = "Clinical probability model for Pulmonary Embolism."
    override val inputs = listOf(
        InputField("dvt", "Clinical signs/symptoms of DVT?", InputType.Choice(listOf("No (0.0 points)", "Yes (+3.0 points)")), "No (0.0 points)"),
        InputField("alt_dx", "PE is #1 dx or equally likely?", InputType.Choice(listOf("No (0.0 points)", "Yes (+3.0 points)")), "No (0.0 points)"),
        InputField("tachycardia", "Heart rate > 100 bpm?", InputType.Choice(listOf("No (0.0 points)", "Yes (+1.5 points)")), "No (0.0 points)"),
        InputField("surgery", "Immobilized >= 3d or surgery in past 4w?", InputType.Choice(listOf("No (0.0 points)", "Yes (+1.5 points)")), "No (0.0 points)"),
        InputField("prior_pe", "Prior DVT or PE?", InputType.Choice(listOf("No (0.0 points)", "Yes (+1.5 points)")), "No (0.0 points)"),
        InputField("hemoptysis", "Hemoptysis present?", InputType.Choice(listOf("No (0.0 points)", "Yes (+1.0 points)")), "No (0.0 points)"),
        InputField("cancer", "Active malignancy within past 6m?", InputType.Choice(listOf("No (0.0 points)", "Yes (+1.0 points)")), "No (0.0 points)")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        var score = 0.0
        
        score += if (values["dvt"]?.contains("Yes") == true) 3.0 else 0.0
        score += if (values["alt_dx"]?.contains("Yes") == true) 3.0 else 0.0
        score += if (values["tachycardia"]?.contains("Yes") == true) 1.5 else 0.0
        score += if (values["surgery"]?.contains("Yes") == true) 1.5 else 0.0
        score += if (values["prior_pe"]?.contains("Yes") == true) 1.5 else 0.0
        score += if (values["hemoptysis"]?.contains("Yes") == true) 1.0 else 0.0
        score += if (values["cancer"]?.contains("Yes") == true) 1.0 else 0.0

        val (interpretation, status) = when {
            score > 4.0 -> "Wells Score > 4.0: PE Likely. Direct to diagnostic imaging (CTPA)." to "danger"
            else -> "Wells Score <= 4.0: PE Unlikely. Consider D-Dimer test to rule out." to "normal"
        }

        return CalculatorResult(
            value = String.format("%.1f points", score),
            interpretation = interpretation,
            status = status
        )
    }
}

// 9. Gestational Weeks & EDD Calculator
object GestationalWeeksCalculator : Calculator() {
    override val id = "gestational"
    override val name = "Gestational Weeks & EDD"
    override val description = "Calculates current Gestational Age and Estimated Date of Delivery (EDD) using Last Menstrual Period (LMP)."
    override val inputs = listOf(
        InputField("day", "LMP Day of Month (1-31)", InputType.Number, "14"),
        InputField("month", "LMP Month (1-12)", InputType.Number, "10"),
        InputField("year", "LMP Year (4-digit)", InputType.Number, "2025")
    )

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val day = values["day"]?.toIntOrNull() ?: return invalidResult()
        val month = values["month"]?.toIntOrNull() ?: return invalidResult()
        val year = values["year"]?.toIntOrNull() ?: return invalidResult()

        if (day !in 1..31 || month !in 1..12 || year < 1900 || year > 2100) {
            return CalculatorResult("Invalid Date", "Please enter a valid calendar date.", "warning")
        }

        try {
            val cal = java.util.Calendar.getInstance().apply {
                isLenient = false
                set(java.util.Calendar.YEAR, year)
                set(java.util.Calendar.MONTH, month - 1)
                set(java.util.Calendar.DAY_OF_MONTH, day)
                set(java.util.Calendar.HOUR_OF_DAY, 0)
                set(java.util.Calendar.MINUTE, 0)
                set(java.util.Calendar.SECOND, 0)
                set(java.util.Calendar.MILLISECOND, 0)
            }
            val lmpMillis = cal.timeInMillis
            val currentMillis = System.currentTimeMillis()

            if (lmpMillis > currentMillis) {
                return CalculatorResult("Future Date", "LMP cannot be in the future.", "warning")
            }

            val diffMillis = currentMillis - lmpMillis
            val diffDays = diffMillis / (1000 * 60 * 60 * 24)
            val weeks = diffDays / 7
            val remainingDays = diffDays % 7

            if (weeks >= 45) {
                return CalculatorResult("> 44 Weeks", "Gestational age exceeds standard pregnancy duration.", "warning")
            }

            val eddCal = java.util.Calendar.getInstance().apply {
                timeInMillis = lmpMillis
                add(java.util.Calendar.DAY_OF_YEAR, 280)
            }
            val eddFormat = String.format("%02d/%02d/%04d", 
                eddCal.get(java.util.Calendar.DAY_OF_MONTH),
                eddCal.get(java.util.Calendar.MONTH) + 1,
                eddCal.get(java.util.Calendar.YEAR)
            )

            val valueString = "$weeks Weeks, $remainingDays Days"
            val interpretation = "Estimated Date of Delivery (EDD): $eddFormat\n(Based on Naegele's Rule: LMP + 280 Days)"

            return CalculatorResult(
                value = valueString,
                interpretation = interpretation,
                status = "normal"
            )
        } catch (e: Exception) {
            return CalculatorResult("Invalid Date", "The specified date does not exist in the calendar.", "warning")
        }
    }
}

// 10. Growth Monitoring (0-5 Years)
object GrowthMonitoringCalculator : Calculator() {
    override val id = "growth"
    override val name = "Child Growth Monitoring"
    override val description = "Evaluates Weight-for-Age and Height-for-Age status in children under 5 using simplified WHO standards."
    override val inputs = listOf(
        InputField("age", "Age (Months, 0-60)", InputType.Number, "12"),
        InputField("gender", "Gender", InputType.Choice(listOf("Boy", "Girl")), "Boy"),
        InputField("weight", "Weight", InputType.Number, "9.5", "kg"),
        InputField("height", "Height", InputType.Number, "75.0", "cm")
    )

    private val ages = doubleArrayOf(0.0, 3.0, 6.0, 9.0, 12.0, 18.0, 24.0, 36.0, 48.0, 60.0)
    
    private val boyWeights = doubleArrayOf(3.3, 6.4, 7.9, 8.9, 9.6, 10.9, 12.2, 14.3, 16.3, 18.3)
    private val girlWeights = doubleArrayOf(3.2, 5.8, 7.3, 8.2, 8.9, 10.2, 11.5, 13.9, 16.1, 18.2)

    private val boyHeights = doubleArrayOf(49.9, 61.4, 67.6, 72.0, 75.7, 82.3, 87.8, 96.1, 103.3, 110.0)
    private val girlHeights = doubleArrayOf(49.1, 59.8, 65.7, 70.1, 74.0, 80.7, 86.4, 95.1, 102.7, 109.4)

    private fun interpolate(age: Double, targetAges: DoubleArray, values: DoubleArray): Double {
        if (age <= targetAges.first()) return values.first()
        if (age >= targetAges.last()) return values.last()
        for (i in 0 until targetAges.size - 1) {
            if (age >= targetAges[i] && age <= targetAges[i + 1]) {
                val ratio = (age - targetAges[i]) / (targetAges[i + 1] - targetAges[i])
                return values[i] + ratio * (values[i + 1] - values[i])
            }
        }
        return values.last()
    }

    override fun calculate(values: Map<String, String>): CalculatorResult {
        val age = values["age"]?.toDoubleOrNull() ?: return invalidResult()
        val gender = values["gender"] ?: "Boy"
        val weight = values["weight"]?.toDoubleOrNull() ?: return invalidResult()
        val height = values["height"]?.toDoubleOrNull() ?: return invalidResult()

        if (age !in 0.0..60.0 || weight <= 0.0 || height <= 0.0) {
            return CalculatorResult("N/A", "Please enter an age between 0 and 60 months, and positive weight/height.", "warning")
        }

        val isBoy = gender.lowercase() == "boy"
        val medianWeight = interpolate(age, ages, if (isBoy) boyWeights else girlWeights)
        val medianHeight = interpolate(age, ages, if (isBoy) boyHeights else girlHeights)

        // Standard Deviation approximations
        val weightSD = medianWeight * 0.12
        val heightSD = medianHeight * 0.04

        val waz = (weight - medianWeight) / weightSD
        val haz = (height - medianHeight) / heightSD

        val weightInterpretation = when {
            waz < -3.0 -> "Severely Underweight (WAZ < -3)"
            waz < -2.0 -> "Underweight (WAZ < -2)"
            waz > 2.0 -> "Overweight (WAZ > +2)"
            else -> "Normal Weight (WAZ: ${String.format("%.1f", waz)})"
        }

        val heightInterpretation = when {
            haz < -3.0 -> "Severely Stunted (HAZ < -3)"
            haz < -2.0 -> "Stunted (HAZ < -2)"
            else -> "Normal Height (HAZ: ${String.format("%.1f", haz)})"
        }

        val overallStatus = if (waz < -2.0 || haz < -2.0 || waz > 2.0) "danger" else "normal"

        return CalculatorResult(
            value = String.format("WAZ: %.1f | HAZ: %.1f", waz, haz),
            interpretation = "Weight Status: $weightInterpretation\nHeight Status: $heightInterpretation\n(Z-scores relative to WHO Growth Standards)",
            status = overallStatus
        )
    }
}

private fun invalidResult(): CalculatorResult {
    return CalculatorResult(
        value = "N/A",
        interpretation = "Please enter valid numeric inputs.",
        status = "warning"
    )
}
