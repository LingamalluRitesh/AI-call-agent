package com.ritesh.aicallassistant.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ritesh.aicallassistant.data.CallItem
import com.ritesh.aicallassistant.data.TranscriptTurn
import com.ritesh.aicallassistant.ui.theme.DarkBackground
import com.ritesh.aicallassistant.ui.theme.DarkSurface
import com.ritesh.aicallassistant.ui.theme.DarkSurfaceVariant
import com.ritesh.aicallassistant.util.PlaybackState

@Composable
fun CallCard(
    call: CallItem,
    isExpanded: Boolean,
    transcripts: List<TranscriptTurn>?,
    isLoadingTranscript: Boolean,
    playbackState: PlaybackState,
    onToggleTranscript: () -> Unit,
    onPlayAudio: () -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val isPlayingThis = when (playbackState) {
        is PlaybackState.Playing -> playbackState.callId == call.id
        else -> false
    }
    val isLoadingAudio = when (playbackState) {
        is PlaybackState.Loading -> playbackState.callId == call.id
        else -> false
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, DarkSurfaceVariant, RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = DarkSurface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Top Row: Number, dial action, time
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable {
                        val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${call.callerNumber}"))
                        context.startActivity(intent)
                    }
                ) {
                    Box(
                        modifier = Modifier
                            .size(32.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF2563EB).copy(alpha = 0.2f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Call,
                            contentDescription = "Call",
                            tint = Color(0xFF60A5FA),
                            modifier = Modifier.size(16.dp)
                        )
                    }
                    Spacer(modifier = Modifier.width(10.dp))
                    Column {
                        Text(
                            text = call.callerName ?: call.callerNumber,
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFF8FAFC)
                        )
                        if (call.callerName != null && call.callerName != call.callerNumber) {
                            Text(
                                text = call.callerNumber,
                                fontSize = 11.sp,
                                color = Color(0xFF94A3B8)
                            )
                        }
                    }
                }

                Text(
                    text = formatDateTime(call.startedAt),
                    fontSize = 11.sp,
                    color = Color(0xFF64748B)
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Badges Row: Urgency, Language, Recording
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                UrgencyBadge(call.urgency)
                LanguageBadge(call.detectedLanguage)
                RecordingBadge(call.recordingStatus, !call.recordingStoragePath.isNullOrBlank())
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Summary box
            Text(
                text = call.summary.ifBlank { "Call handled by AI receptionist." },
                fontSize = 13.sp,
                lineHeight = 18.sp,
                color = Color(0xFFCBD5E1)
            )

            // Audio player bar (if recorded)
            if (call.recordingStatus == "recording" && !call.recordingStoragePath.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(12.dp))
                AudioPlayerBar(
                    isPlaying = isPlayingThis,
                    isLoading = isLoadingAudio,
                    onPlayPause = onPlayAudio
                )
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Transcript toggle
            Row(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { onToggleTranscript() }
                    .padding(vertical = 4.dp, horizontal = 2.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (isExpanded) "Hide Transcript ▲" else "View Transcript ▼",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFF38BDF8)
                )
                if (isLoadingTranscript) {
                    Spacer(modifier = Modifier.width(8.dp))
                    CircularProgressIndicator(
                        modifier = Modifier.size(12.dp),
                        strokeWidth = 2.dp,
                        color = Color(0xFF38BDF8)
                    )
                }
            }

            // Expanded transcript list
            AnimatedVisibility(
                visible = isExpanded,
                enter = fadeIn() + expandVertically(),
                exit = fadeOut() + shrinkVertically()
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 10.dp)
                        .clip(RoundedCornerShape(12.dp))
                        .background(DarkBackground)
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "Turn-by-turn dialogue:",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color(0xFF64748B)
                    )

                    if (transcripts.isNullOrEmpty()) {
                        Text(
                            text = if (isLoadingTranscript) "Loading dialogue..." else "No transcript available.",
                            fontSize = 12.sp,
                            color = Color(0xFF64748B)
                        )
                    } else {
                        transcripts.forEach { turn ->
                            val isAssistant = turn.speaker.lowercase() == "assistant"
                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(
                                        if (isAssistant) Color(0xFF1E293B) else Color(0xFF161F30)
                                    )
                                    .padding(8.dp)
                            ) {
                                Text(
                                    text = if (isAssistant) "🤖 AI Receptionist" else "👤 Caller",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isAssistant) Color(0xFF93C5FD) else Color(0xFF34D399)
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = turn.content,
                                    fontSize = 12.sp,
                                    color = Color(0xFFF1F5F9),
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AudioPlayerBar(
    isPlaying: Boolean,
    isLoading: Boolean,
    onPlayPause: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(DarkSurfaceVariant)
            .clickable { onPlayPause() }
            .padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(Color(0xFF2563EB)),
                contentAlignment = Alignment.Center
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(14.dp),
                        strokeWidth = 2.dp,
                        color = Color.White
                    )
                } else {
                    Icon(
                        imageVector = if (isPlaying) Icons.Default.Close else Icons.Default.PlayArrow,
                        contentDescription = if (isPlaying) "Stop" else "Play",
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
            Spacer(modifier = Modifier.width(10.dp))
            Column {
                Text(
                    text = if (isPlaying) "Playing Call Recording" else "Play Recording",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color(0xFFF8FAFC)
                )
                Text(
                    text = "8kHz mono PCM WAV (Consent Granted)",
                    fontSize = 10.sp,
                    color = Color(0xFF94A3B8)
                )
            }
        }
        Icon(
            imageVector = Icons.Default.Check,
            contentDescription = null,
            tint = Color(0xFF34D399),
            modifier = Modifier.size(16.dp)
        )
    }
}

@Composable
private fun UrgencyBadge(urgency: String) {
    val (bgColor, textColor, border, label) = when (urgency.lowercase()) {
        "emergency" -> Quad(Color(0xFFEF4444).copy(alpha = 0.15f), Color(0xFFF87171), Color(0xFFEF4444).copy(alpha = 0.3f), "EMERGENCY")
        "high" -> Quad(Color(0xFFF59E0B).copy(alpha = 0.15f), Color(0xFFFBBF24), Color(0xFFF59E0B).copy(alpha = 0.3f), "HIGH")
        else -> Quad(Color(0xFF3B82F6).copy(alpha = 0.15f), Color(0xFF60A5FA), Color(0xFF3B82F6).copy(alpha = 0.3f), "NORMAL")
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .border(1.dp, border, RoundedCornerShape(6.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            if (urgency.lowercase() == "emergency") {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = textColor,
                    modifier = Modifier.size(10.dp)
                )
                Spacer(modifier = Modifier.width(3.dp))
            }
            Text(
                text = label,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold,
                color = textColor
            )
        }
    }
}

@Composable
private fun LanguageBadge(lang: String) {
    val label = when (lang.lowercase()) {
        "te", "telugu" -> "TELUGU"
        "hi", "hindi" -> "HINDI"
        else -> "ENGLISH"
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(DarkSurfaceVariant)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = label,
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color(0xFF94A3B8)
        )
    }
}

@Composable
private fun RecordingBadge(status: String, hasAudio: Boolean) {
    val isRecorded = status == "recording" || hasAudio
    val (bgColor, textColor, label) = if (isRecorded) {
        Triple(Color(0xFF10B981).copy(alpha = 0.15f), Color(0xFF34D399), "REC SAVED")
    } else {
        Triple(Color(0xFF64748B).copy(alpha = 0.15f), Color(0xFF94A3B8), "NO REC")
    }

    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(6.dp))
            .background(bgColor)
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = label,
            fontSize = 10.sp,
            fontWeight = FontWeight.SemiBold,
            color = textColor
        )
    }
}

private fun formatDateTime(isoString: String): String {
    if (isoString.isBlank()) return "Recent"
    return try {
        // Simple clean formatting
        val cleaned = isoString.replace("T", " ").substringBefore(".")
        if (cleaned.length >= 16) cleaned.substring(5, 16) else cleaned
    } catch (_: Exception) {
        isoString
    }
}

private data class Quad<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
