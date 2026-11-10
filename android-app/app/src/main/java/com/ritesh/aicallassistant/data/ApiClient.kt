package com.ritesh.aicallassistant.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL

class ApiClient(private var baseUrlProvider: () -> String) {

    private val baseUrl: String
        get() {
            var url = baseUrlProvider().trim()
            if (!url.endsWith("/")) {
                url += "/"
            }
            return url
        }

    suspend fun checkHealth(): Result<Boolean> = withContext(Dispatchers.IO) {
        runCatching {
            val url = URL(baseUrl + "health")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                connectTimeout = 4000
                readTimeout = 4000
                requestMethod = "GET"
            }
            conn.responseCode in 200..299
        }
    }

    suspend fun getStats(): Result<DashboardStats> = withContext(Dispatchers.IO) {
        runCatching {
            val jsonStr = httpGet("api/dashboard/stats")
            val obj = JSONObject(jsonStr)
            DashboardStats(
                totalCalls = obj.optInt("total_calls", 0),
                callsToday = obj.optInt("calls_today", 0),
                unreadMessages = obj.optInt("unread_messages", 0),
                recordedCalls = obj.optInt("recorded_calls", 0),
                emergencyCalls = obj.optInt("emergency_calls", 0)
            )
        }
    }

    suspend fun getCalls(limit: Int = 50): Result<List<CallItem>> = withContext(Dispatchers.IO) {
        runCatching {
            val jsonStr = httpGet("api/calls?limit=$limit")
            val root = JSONObject(jsonStr)
            val items = root.optJSONArray("items") ?: JSONArray()
            val list = mutableListOf<CallItem>()

            for (i in 0 until items.length()) {
                val item = items.getJSONObject(i)
                list.add(parseCallItem(item))
            }
            list
        }
    }

    suspend fun getCallDetail(callId: String): Result<Pair<CallItem, List<TranscriptTurn>>> = withContext(Dispatchers.IO) {
        runCatching {
            val jsonStr = httpGet("api/calls/$callId")
            val obj = JSONObject(jsonStr)
            val callItem = parseCallItem(obj)
            val turnsArray = obj.optJSONArray("transcripts") ?: JSONArray()
            val transcripts = mutableListOf<TranscriptTurn>()

            for (i in 0 until turnsArray.length()) {
                val t = turnsArray.getJSONObject(i)
                transcripts.add(
                    TranscriptTurn(
                        id = t.optString("id", i.toString()),
                        speaker = t.optString("speaker", "caller"),
                        content = t.optString("content", ""),
                        createdAt = t.optString("created_at", "")
                    )
                )
            }
            Pair(callItem, transcripts)
        }
    }

    suspend fun simulateCall(scenario: SimulationScenario): Result<String> = withContext(Dispatchers.IO) {
        runCatching {
            val payload = JSONObject().apply {
                put("caller_number", scenario.callerNumber)
                put("language", scenario.language)
                val utts = JSONArray()
                scenario.utterances.forEach { utts.put(it) }
                put("caller_utterances", utts)
            }

            val responseStr = httpPost("api/test/simulate-call", payload.toString())
            val respObj = JSONObject(responseStr)
            respObj.optString("call_id", "simulated")
        }
    }

    fun getRecordingAudioUrl(filename: String): String {
        val cleanName = filename.replace("\\", "/").substringAfterLast("/")
        return baseUrl + "api/recordings/" + cleanName
    }

    private fun parseCallItem(obj: JSONObject): CallItem {
        return CallItem(
            id = obj.optString("id", ""),
            callerNumber = obj.optString("caller_number", "Unknown"),
            startedAt = obj.optString("started_at", obj.optString("created_at", "")),
            durationSeconds = obj.optInt("duration_seconds", 0),
            summary = obj.optString("summary", "Call handled by AI receptionist."),
            urgency = obj.optString("urgency", "normal"),
            detectedLanguage = obj.optString("detected_language", "en"),
            consentStatus = obj.optString("consent_status", "unknown"),
            recordingStatus = obj.optString("recording_status", "not_recorded"),
            recordingStoragePath = if (obj.isNull("recording_storage_path")) null else obj.optString("recording_storage_path"),
            callbackRequired = obj.optBoolean("callback_required", false),
            callerName = if (obj.isNull("caller_name")) null else obj.optString("caller_name")
        )
    }

    private fun httpGet(endpoint: String): String {
        val url = URL(baseUrl + endpoint)
        val conn = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 7000
            readTimeout = 7000
            requestMethod = "GET"
            setRequestProperty("Accept", "application/json")
        }

        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            ?: throw IllegalStateException("HTTP $code without error stream")
        return BufferedReader(InputStreamReader(stream)).use { it.readText() }
    }

    private fun httpPost(endpoint: String, jsonBody: String): String {
        val url = URL(baseUrl + endpoint)
        val conn = (url.openConnection() as HttpURLConnection).apply {
            connectTimeout = 15000
            readTimeout = 25000
            requestMethod = "POST"
            doOutput = true
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Accept", "application/json")
        }

        OutputStreamWriter(conn.outputStream).use { it.write(jsonBody) }

        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            ?: throw IllegalStateException("HTTP $code without error stream")
        return BufferedReader(InputStreamReader(stream)).use { it.readText() }
    }
}
