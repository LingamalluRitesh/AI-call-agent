package com.ritesh.aicallassistant.ui

import android.app.Application
import android.content.Context
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.ritesh.aicallassistant.BuildConfig
import com.ritesh.aicallassistant.data.*
import com.ritesh.aicallassistant.util.AudioPlayerManager
import com.ritesh.aicallassistant.util.PlaybackState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AssistantUiState(
    val stats: DashboardStats = DashboardStats(),
    val calls: List<CallItem> = emptyList(),
    val filteredCalls: List<CallItem> = emptyList(),
    val currentFilter: CallFilter = CallFilter.ALL,
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isSimulating: Boolean = false,
    val serverOnline: Boolean? = null,
    val serverUrl: String = "",
    val expandedCallIds: Set<String> = emptySet(),
    val transcripts: Map<String, List<TranscriptTurn>> = emptyMap(),
    val loadingTranscripts: Set<String> = emptySet(),
    val snackbarMessage: String? = null
)

class AssistantViewModel(application: Application) : AndroidViewModel(application) {

    private val prefs = application.getSharedPreferences("ritesh_call_assistant_prefs", Context.MODE_PRIVATE)
    private val audioPlayerManager = AudioPlayerManager()

    val playbackState: StateFlow<PlaybackState> = audioPlayerManager.state

    private val _uiState = MutableStateFlow(
        AssistantUiState(
            serverUrl = prefs.getString("server_url", BuildConfig.API_BASE_URL) ?: BuildConfig.API_BASE_URL
        )
    )
    val uiState: StateFlow<AssistantUiState> = _uiState.asStateFlow()

    private val apiClient = ApiClient { _uiState.value.serverUrl }

    init {
        refreshAll()
    }

    fun refreshAll(isPullRefresh: Boolean = false) {
        viewModelScope.launch {
            if (isPullRefresh) {
                _uiState.value = _uiState.value.copy(isRefreshing = true)
            } else {
                _uiState.value = _uiState.value.copy(isLoading = true)
            }

            val healthResult = apiClient.checkHealth()
            val isOnline = healthResult.getOrDefault(false)

            val statsResult = apiClient.getStats()
            val callsResult = apiClient.getCalls(limit = 50)

            val newStats = statsResult.getOrDefault(_uiState.value.stats)
            val newCalls = callsResult.getOrDefault(_uiState.value.calls)

            val filtered = applyFilter(newCalls, _uiState.value.currentFilter)

            _uiState.value = _uiState.value.copy(
                stats = newStats,
                calls = newCalls,
                filteredCalls = filtered,
                serverOnline = isOnline,
                isLoading = false,
                isRefreshing = false
            )
        }
    }

    fun setFilter(filter: CallFilter) {
        val filtered = applyFilter(_uiState.value.calls, filter)
        _uiState.value = _uiState.value.copy(
            currentFilter = filter,
            filteredCalls = filtered
        )
    }

    private fun applyFilter(calls: List<CallItem>, filter: CallFilter): List<CallItem> {
        return when (filter) {
            CallFilter.ALL -> calls
            CallFilter.CALLBACKS -> calls.filter { it.callbackRequired || it.urgency == "high" || it.urgency == "emergency" }
            CallFilter.RECORDINGS -> calls.filter { it.recordingStatus == "recording" && !it.recordingStoragePath.isNullOrBlank() }
        }
    }

    fun setServerUrl(newUrl: String) {
        var cleanUrl = newUrl.trim()
        if (!cleanUrl.endsWith("/")) {
            cleanUrl += "/"
        }
        prefs.edit().putString("server_url", cleanUrl).apply()
        _uiState.value = _uiState.value.copy(serverUrl = cleanUrl)
        refreshAll()
    }

    fun toggleTranscript(callId: String) {
        val currentExpanded = _uiState.value.expandedCallIds
        if (currentExpanded.contains(callId)) {
            _uiState.value = _uiState.value.copy(expandedCallIds = currentExpanded - callId)
            return
        }

        _uiState.value = _uiState.value.copy(
            expandedCallIds = currentExpanded + callId
        )

        if (!_uiState.value.transcripts.containsKey(callId)) {
            fetchTranscript(callId)
        }
    }

    private fun fetchTranscript(callId: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                loadingTranscripts = _uiState.value.loadingTranscripts + callId
            )
            val result = apiClient.getCallDetail(callId)
            result.onSuccess { pair ->
                _uiState.value = _uiState.value.copy(
                    transcripts = _uiState.value.transcripts + (callId to pair.second),
                    loadingTranscripts = _uiState.value.loadingTranscripts - callId
                )
            }.onFailure {
                _uiState.value = _uiState.value.copy(
                    loadingTranscripts = _uiState.value.loadingTranscripts - callId,
                    snackbarMessage = "Could not load transcript: ${it.localizedMessage}"
                )
            }
        }
    }

    fun playRecording(call: CallItem) {
        val path = call.recordingStoragePath ?: return
        val url = apiClient.getRecordingAudioUrl(path)
        audioPlayerManager.play(call.id, url)
    }

    fun stopAudio() {
        audioPlayerManager.stop()
    }

    fun runSimulation(scenario: SimulationScenario) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSimulating = true)
            val result = apiClient.simulateCall(scenario)
            result.onSuccess {
                _uiState.value = _uiState.value.copy(
                    isSimulating = false,
                    snackbarMessage = "Test call processed: ${scenario.title}"
                )
                refreshAll(isPullRefresh = false)
            }.onFailure { err ->
                _uiState.value = _uiState.value.copy(
                    isSimulating = false,
                    snackbarMessage = "Simulation failed: ${err.localizedMessage}"
                )
            }
        }
    }

    fun clearSnackbar() {
        _uiState.value = _uiState.value.copy(snackbarMessage = null)
    }

    override fun onCleared() {
        super.onCleared()
        audioPlayerManager.stop()
    }
}
