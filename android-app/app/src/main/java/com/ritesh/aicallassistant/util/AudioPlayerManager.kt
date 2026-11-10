package com.ritesh.aicallassistant.util

import android.media.AudioAttributes
import android.media.MediaPlayer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

sealed class PlaybackState {
    object Idle : PlaybackState()
    data class Loading(val callId: String) : PlaybackState()
    data class Playing(val callId: String) : PlaybackState()
    data class Paused(val callId: String) : PlaybackState()
    data class Error(val callId: String, val message: String) : PlaybackState()
}

class AudioPlayerManager {
    private var mediaPlayer: MediaPlayer? = null
    private var currentCallId: String? = null

    private val _state = MutableStateFlow<PlaybackState>(PlaybackState.Idle)
    val state: StateFlow<PlaybackState> = _state.asStateFlow()

    fun play(callId: String, audioUrl: String) {
        if (currentCallId == callId && mediaPlayer != null) {
            if (mediaPlayer?.isPlaying == true) {
                mediaPlayer?.pause()
                _state.value = PlaybackState.Paused(callId)
                return
            } else {
                mediaPlayer?.start()
                _state.value = PlaybackState.Playing(callId)
                return
            }
        }

        stop()
        currentCallId = callId
        _state.value = PlaybackState.Loading(callId)

        try {
            val player = MediaPlayer().apply {
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
                        .setUsage(AudioAttributes.USAGE_MEDIA)
                        .build()
                )
                setDataSource(audioUrl)
                setOnPreparedListener { mp ->
                    mp.start()
                    _state.value = PlaybackState.Playing(callId)
                }
                setOnCompletionListener {
                    _state.value = PlaybackState.Idle
                    currentCallId = null
                }
                setOnErrorListener { _, what, extra ->
                    _state.value = PlaybackState.Error(callId, "Audio playback error: ($what, $extra)")
                    currentCallId = null
                    true
                }
                prepareAsync()
            }
            mediaPlayer = player
        } catch (e: Exception) {
            _state.value = PlaybackState.Error(callId, e.message ?: "Failed to play audio")
            currentCallId = null
        }
    }

    fun stop() {
        try {
            mediaPlayer?.stop()
            mediaPlayer?.release()
        } catch (_: Exception) {
        } finally {
            mediaPlayer = null
            currentCallId = null
            _state.value = PlaybackState.Idle
        }
    }
}
