package com.ritesh.aicallassistant.data

data class DashboardStats(
    val totalCalls: Int = 0,
    val callsToday: Int = 0,
    val unreadMessages: Int = 0,
    val recordedCalls: Int = 0,
    val emergencyCalls: Int = 0
)

data class CallItem(
    val id: String,
    val callerNumber: String,
    val startedAt: String,
    val durationSeconds: Int = 0,
    val summary: String,
    val urgency: String = "normal", // "normal", "high", "emergency"
    val detectedLanguage: String = "en",
    val consentStatus: String = "unknown",
    val recordingStatus: String = "not_recorded",
    val recordingStoragePath: String? = null,
    val callbackRequired: Boolean = false,
    val callerName: String? = null
)

data class TranscriptTurn(
    val id: String,
    val speaker: String, // "caller", "assistant"
    val content: String,
    val createdAt: String = ""
)

enum class CallFilter {
    ALL,
    CALLBACKS,
    RECORDINGS
}

data class SimulationScenario(
    val title: String,
    val subtitle: String,
    val callerNumber: String,
    val language: String,
    val utterances: List<String>
)
