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
        WellsPeCalculator
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

private fun invalidResult(): CalculatorResult {
    return CalculatorResult(
        value = "N/A",
        interpretation = "Please enter valid numeric inputs.",
        status = "warning"
    )
}
