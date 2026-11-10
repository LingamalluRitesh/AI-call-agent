package com.ritesh.aicallassistant.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ritesh.aicallassistant.data.DashboardStats
import com.ritesh.aicallassistant.ui.theme.DarkSurface
import com.ritesh.aicallassistant.ui.theme.DarkSurfaceVariant

@Composable
fun StatsRow(
    stats: DashboardStats,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        StatItem(
            value = stats.callsToday.toString(),
            label = "Calls Today",
            valueColor = Color(0xFF38BDF8),
            modifier = Modifier.weight(1f)
        )
        StatItem(
            value = stats.unreadMessages.toString(),
            label = "Callbacks",
            valueColor = if (stats.unreadMessages > 0) Color(0xFFF59E0B) else Color(0xFF38BDF8),
            modifier = Modifier.weight(1f)
        )
        StatItem(
            value = stats.recordedCalls.toString(),
            label = "Recorded",
            valueColor = Color(0xFF34D399),
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun StatItem(
    value: String,
    label: String,
    valueColor: Color,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(14.dp))
            .background(DarkSurface)
            .border(1.dp, DarkSurfaceVariant, RoundedCornerShape(14.dp))
            .padding(vertical = 12.dp, horizontal = 10.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = value,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
                color = valueColor
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = label,
                fontSize = 11.sp,
                fontWeight = FontWeight.Medium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
