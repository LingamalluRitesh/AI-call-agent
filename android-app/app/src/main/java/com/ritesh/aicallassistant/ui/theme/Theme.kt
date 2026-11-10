package com.ritesh.aicallassistant.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val DarkBackground = Color(0xFF0B0F19)
val DarkSurface = Color(0xFF161F30)
val DarkSurfaceVariant = Color(0xFF1E293B)
val BrandPrimary = Color(0xFF38BDF8)
val BrandSecondary = Color(0xFF2563EB)
val TextPrimary = Color(0xFFF8FAFC)
val TextSecondary = Color(0xFF94A3B8)
val StatusGreen = Color(0xFF22C55E)
val StatusAmber = Color(0xFFF59E0B)
val StatusRed = Color(0xFFEF4444)

private val AppColorScheme = darkColorScheme(
    primary = BrandPrimary,
    onPrimary = Color(0xFF003258),
    primaryContainer = BrandSecondary,
    onPrimaryContainer = Color.White,
    secondary = Color(0xFF818CF8),
    background = DarkBackground,
    onBackground = TextPrimary,
    surface = DarkSurface,
    onSurface = TextPrimary,
    surfaceVariant = DarkSurfaceVariant,
    onSurfaceVariant = TextSecondary,
    error = StatusRed,
    onError = Color.White
)

@Composable
fun RiteshCallAssistantTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AppColorScheme,
        content = content
    )
}
