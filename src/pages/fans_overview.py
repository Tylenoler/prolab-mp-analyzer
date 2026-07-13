"""
关注者分析页面 — 增长趋势、关键指标。全中文。
支持时间段筛选和鼠标悬停精确数据提示。
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

try:
    import mplcursors
    HAS_MPLCURSORS = True
except ImportError:
    HAS_MPLCURSORS = False

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QButtonGroup, QPushButton
)
from PySide6.QtCore import Qt

CJK = "Microsoft YaHei"
COLORS = {
    'card_bg': '#FFFFFF', 'primary': '#3B82F6', 'text_dark': '#1F2937',
    'text_secondary': '#6B7280', 'border': '#E5E7EB', 'success': '#10B981',
    'warning': '#F59E0B', 'danger': '#EF4444',
}
CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4']

plt.rcParams['font.sans-serif'] = [CJK, 'SimHei', 'Noto Sans SC', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def _make_card(colors):
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{ background: {colors['card_bg']}; border: 1px solid {colors['border']}; border-radius: 12px; }}
    """)
    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    return card


def _make_kpi(title, value, accent, colors):
    card = QFrame()
    card.setFixedHeight(90)
    card.setStyleSheet(f"""
        QFrame {{ background: white; border: 1px solid {colors['border']};
                  border-left: 4px solid {accent}; border-radius: 10px; }}
    """)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 12)
    lbl_t = QLabel(title)
    lbl_t.setStyleSheet(f"font-size: 12px; color: {colors['text_secondary']}; border: none; background: transparent; font-family: '{CJK}';")
    lbl_v = QLabel(value)
    lbl_v.setObjectName("kpi_value")
    lbl_v.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {colors['text_dark']}; border: none; background: transparent; font-family: '{CJK}';")
    layout.addWidget(lbl_t)
    layout.addWidget(lbl_v)
    layout.addStretch()
    return card


class FansOverviewPage(QWidget):
    TIME_RANGES = [
        ("全量", "all"),
        ("今年", "year"),
        ("一年", "1y"),
        ("6个月", "6m"),
        ("3个月", "3m"),
        ("1个月", "1m"),
        ("7天", "7d"),
    ]

    def __init__(self, colors=None, parent=None):
        super().__init__(parent)
        self.colors = colors or COLORS
        self.data = None
        self.read_data = None
        self.current_range = 'all'
        self.range_btns = {}
        self._cursors = []
        self._init_ui()

    def set_read_data(self, read_data):
        self.read_data = read_data

    def _init_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # === Time Range Filter ===
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        filter_row.addStretch()
        filter_label = QLabel("时间范围:")
        filter_label.setStyleSheet(f"font-size: 12px; color: {self.colors['text_secondary']}; font-family: '{CJK}';")
        filter_row.addWidget(filter_label)

        self.range_group = QButtonGroup(self)
        self.range_group.setExclusive(True)
        for text, key in self.TIME_RANGES:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(52)
            btn.setCursor(Qt.PointingHandCursor)
            self.range_group.addButton(btn)
            self.range_btns[key] = btn
            btn.clicked.connect(lambda checked, k=key: self._on_range_change(k))
            filter_row.addWidget(btn)
        self.range_btns['all'].setChecked(True)
        self._update_button_styles()
        layout.addLayout(filter_row)

        # === KPI ===
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(16)
        self.kpi_total = _make_kpi("累计关注", "—", self.colors['primary'], self.colors)
        self.kpi_gain = _make_kpi("净增长", "—", self.colors['success'], self.colors)
        self.kpi_peak = _make_kpi("单日最高增长", "—", self.colors['warning'], self.colors)
        self.kpi_avg = _make_kpi("日均增长", "—", '#8B5CF6', self.colors)
        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_gain)
        kpi_layout.addWidget(self.kpi_peak)
        kpi_layout.addWidget(self.kpi_avg)
        self.kpi_week_gain = _make_kpi("关注周环比", "—", '#F97316', self.colors)
        self.kpi_accel = _make_kpi("增长加速度", "—", '#EC4899', self.colors)
        kpi_layout.addWidget(self.kpi_week_gain)
        kpi_layout.addWidget(self.kpi_accel)
        layout.addLayout(kpi_layout)

        # === Trend Chart ===
        trend_card = _make_card(self.colors)
        tl = QVBoxLayout(trend_card)
        tl.setContentsMargins(16, 12, 16, 8)
        trend_title = QLabel("关注者增长趋势")
        trend_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        tl.addWidget(trend_title)
        self.trend_fig = Figure(figsize=(8, 3.5), dpi=100, facecolor='white')
        self.trend_canvas = FigureCanvas(self.trend_fig)
        self.trend_canvas.setStyleSheet("background: white;")
        tl.addWidget(self.trend_canvas)
        layout.addWidget(trend_card)

        # === Daily Breakdown Chart ===
        breakdown_card = _make_card(self.colors)
        bl = QVBoxLayout(breakdown_card)
        bl.setContentsMargins(16, 12, 16, 8)
        breakdown_title = QLabel("每日关注构成（新增 / 取消 / 净增）")
        breakdown_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        bl.addWidget(breakdown_title)
        self.breakdown_fig = Figure(figsize=(8, 3), dpi=100, facecolor='white')
        self.breakdown_canvas = FigureCanvas(self.breakdown_fig)
        self.breakdown_canvas.setStyleSheet("background: white;")
        bl.addWidget(self.breakdown_canvas)
        layout.addWidget(breakdown_card)

        # === Acceleration Chart ===
        accel_card = _make_card(self.colors)
        acl = QVBoxLayout(accel_card)
        acl.setContentsMargins(16, 12, 16, 8)
        accel_title = QLabel("增长加速度（日增量变化率）")
        accel_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        acl.addWidget(accel_title)
        self.accel_fig = Figure(figsize=(8, 2.5), dpi=100, facecolor='white')
        self.accel_canvas = FigureCanvas(self.accel_fig)
        self.accel_canvas.setStyleSheet("background: white;")
        acl.addWidget(self.accel_canvas)
        layout.addWidget(accel_card)

        # === Placeholder ===
        self.placeholder = QLabel(
            "尚未导入关注者数据\n\n"
            "将关注者数据文件（.xls）放入 DATA/FANS 文件夹\n"
            "然后点击「Import Data」选择该文件夹"
        )
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            font-size: 14px; color: {self.colors['text_secondary']}; font-family: "{CJK}";
            padding: 60px; border: 2px dashed {self.colors['border']};
            border-radius: 12px; background: white;
        """)
        layout.addWidget(self.placeholder)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    # === Time Range ===

    def _on_range_change(self, key):
        self.current_range = key
        self._update_button_styles()
        self._refresh_all()

    def _update_button_styles(self):
        active_bg = self.colors['primary']
        for key, btn in self.range_btns.items():
            if key == self.current_range:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {active_bg}; color: white;
                        border: none; border-radius: 6px;
                        font-size: 12px; font-family: "{CJK}"; font-weight: bold;
                        padding: 0 14px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #E5E7EB; color: #374151;
                        border: none; border-radius: 6px;
                        font-size: 12px; font-family: "{CJK}";
                        padding: 0 14px;
                    }}
                    QPushButton:hover {{ background: #D1D5DB; }}
                """)

    def _get_date_range(self):
        now = pd.Timestamp.now()
        range_map = {
            'all':  (None, None),
            'year': (pd.Timestamp(now.year, 1, 1), now),
            '1y':   (now - pd.DateOffset(years=1), now),
            '6m':   (now - pd.DateOffset(months=6), now),
            '3m':   (now - pd.DateOffset(months=3), now),
            '1m':   (now - pd.DateOffset(months=1), now),
            '7d':   (now - pd.Timedelta(days=7), now),
        }
        return range_map.get(self.current_range, (None, None))

    def _filter_data(self, data):
        if not data or 'fans_data' not in data:
            return {}
        start, end = self._get_date_range()
        if start is None:
            return data
        df = data['fans_data']
        dates = pd.to_datetime(df['date'], errors='coerce')
        mask = (dates >= start) & (dates <= end)
        filtered = df[mask].copy()
        if filtered.empty:
            return {}
        return {'fans_data': filtered}

    # === Data Update ===

    def update_data(self, data):
        self.data = data
        self._refresh_all()

    def _refresh_all(self):
        data = self._filter_data(self.data)
        if not data or 'fans_data' not in data:
            self.placeholder.show()
            self._show_empty()
            return
        self.placeholder.hide()
        self._update_kpis(data)
        self._draw_trend(data)
        self._draw_breakdown(data)
        self._draw_accel(data)

    def _show_empty(self):
        self._set_kpi(self.kpi_total, "—")
        self._set_kpi(self.kpi_gain, "—")
        self._set_kpi(self.kpi_peak, "—")
        self._set_kpi(self.kpi_avg, "—")
        self._set_kpi(self.kpi_week_gain, "—")
        self._set_kpi(self.kpi_accel, "—")
        self._clear_cursors()
        self.trend_fig.clear()
        ax = self.trend_fig.add_subplot(111)
        ax.text(0.5, 0.5, '所选时间段内暂无数据',
                ha='center', va='center', fontsize=14, color='#999', fontfamily=CJK)
        ax.set_axis_off()
        self.trend_canvas.draw()
        self.breakdown_fig.clear()
        ax2 = self.breakdown_fig.add_subplot(111)
        ax2.text(0.5, 0.5, '所选时间段内暂无数据',
                ha='center', va='center', fontsize=14, color='#999', fontfamily=CJK)
        ax2.set_axis_off()
        self.breakdown_canvas.draw()
        self.accel_fig.clear()
        ax3 = self.accel_fig.add_subplot(111)
        ax3.text(0.5, 0.5, '所选时间段内暂无数据',
                ha='center', va='center', fontsize=14, color='#999', fontfamily=CJK)
        ax3.set_axis_off()
        self.accel_canvas.draw()

    # === KPIs ===

    def _update_kpis(self, data):
        df = data['fans_data'].sort_values('date')
        col = '累积关注人数'
        if col in df.columns:
            total = df[col].iloc[-1]
            gain = df[col].iloc[-1] - df[col].dropna().iloc[0]
        elif len(df.columns) > 1:
            col = [c for c in df.columns if c != 'date'][-1]
            total = df[col].iloc[-1]
            gain = df[col].dropna().iloc[-1] - df[col].dropna().iloc[0]
        else:
            return

        daily_diff = df[col].diff().dropna()
        peak = int(daily_diff.max()) if not daily_diff.empty else 0
        avg = daily_diff.mean() if not daily_diff.empty else 0

        self._set_kpi(self.kpi_total, f"{int(total):,}")
        self._set_kpi(self.kpi_gain, f"{int(gain):+}")
        self._set_kpi(self.kpi_peak, f"{peak:,}")
        self._set_kpi(self.kpi_avg, f"{avg:,.1f}")

        # Week-over-week growth
        if len(df) >= 14:
            this_week = df.tail(7)
            prev_week = df.iloc[-14:-7]
            tw_avg = this_week['净增关注人数'].mean() if '净增关注人数' in this_week.columns else 0
            pw_avg = prev_week['净增关注人数'].mean() if '净增关注人数' in prev_week.columns else 0
            if pw_avg and pw_avg != 0:
                pct = (tw_avg - pw_avg) / pw_avg * 100
                self._set_kpi(self.kpi_week_gain, f"{pct:+.1f}%")
        # Acceleration (second derivative of cumulative)
        accel = daily_diff.diff().dropna()
        if not accel.empty:
            avg_accel = accel.mean()
            self._set_kpi(self.kpi_accel, f"{avg_accel:+.1f}")

    def _set_kpi(self, card, value):
        lbl = card.findChild(QLabel, "kpi_value")
        if lbl:
            lbl.setText(value)

    # === Chart ===

    def _draw_trend(self, data):
        self._clear_cursors()
        self.trend_fig.clear()
        ax = self.trend_fig.add_subplot(111)
        df = data['fans_data'].sort_values('date')

        if '累积关注人数' in df.columns:
            col = '累积关注人数'
        else:
            numeric = [c for c in df.columns if c != 'date']
            if not numeric:
                self.trend_canvas.draw()
                return
            col = numeric[-1]

        ax.fill_between(df['date'], df[col], alpha=0.15, color=CHART_COLORS[0])
        ax.plot(df['date'], df[col], color=CHART_COLORS[0], linewidth=2, marker='o', markersize=3)
        ax.set_ylabel('累积关注人数', fontsize=10, color='#666')

        # Right axis: daily delta
        daily = df[col].diff()
        ax2 = ax.twinx()
        ax2.bar(df['date'], daily, alpha=0.3, color=CHART_COLORS[1], width=0.8)
        ax2.set_ylabel('日增量', fontsize=10, color='#888')
        ax2.spines['top'].set_visible(False)
        ax2.tick_params(colors='#888', labelsize=9)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E5E7EB')
        ax.spines['bottom'].set_color('#E5E7EB')
        ax.tick_params(colors='#888', labelsize=9)
        ax.grid(axis='y', alpha=0.3, color='#E5E7EB')

        # 7-day and 30-day moving averages
        if len(df) >= 7:
            df['ma7'] = df[col].rolling(7, min_periods=7).mean()
            ax.plot(df['date'], df['ma7'], color=CHART_COLORS[2],
                    linewidth=1.5, linestyle='--', alpha=0.7, label='7日平均')
        if len(df) >= 30:
            df['ma30'] = df[col].rolling(30, min_periods=30).mean()
            ax.plot(df['date'], df['ma30'], color=CHART_COLORS[4],
                    linewidth=1.5, linestyle=':', alpha=0.6, label='30日平均')

        ax.legend(fontsize=8, loc='upper left')
        self.trend_fig.subplots_adjust(left=0.08, right=0.88, top=0.95, bottom=0.25)
        self.trend_canvas.draw()

        # Hover tooltip — only on data points, not on line segments
        if HAS_MPLCURSORS:
            scatter = ax.scatter(df['date'], df[col], s=20, color=CHART_COLORS[0], zorder=5)
            cursor = mplcursors.cursor(scatter, hover=mplcursors.HoverMode.Transient)
            @cursor.connect("add")
            def on_add(sel):
                idx = sel.index
                row = df.iloc[idx]
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                cumulative = int(row[col])
                d = daily.iloc[idx] if idx < len(daily) else 0
                d_str = f"+{int(d)}" if d >= 0 else str(int(d))
                sel.annotation.set_text(f" {date_str}  累积: {cumulative:,}  日增量: {d_str}")
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95, ec="#D1D5DB", lw=0.5)
                sel.annotation.set_fontsize(9)
                sel.annotation.set_fontfamily(CJK)
            self._cursors.append(cursor)

    def _draw_breakdown(self, data):
        """Draw daily new/unfollow/net-change stacked bar chart."""
        self.breakdown_fig.clear()
        ax = self.breakdown_fig.add_subplot(111)
        df = data['fans_data'].sort_values('date')

        new_col = '新关注人数'
        unfo_col = '取消关注人数'
        net_col = '净增关注人数'

        has_new = new_col in df.columns
        has_unfo = unfo_col in df.columns
        has_net = net_col in df.columns

        if not has_net and not (has_new and has_unfo):
            ax.text(0.5, 0.5, '暂无明细数据', ha='center', va='center', fontsize=14, color='#999', fontfamily=CJK)
            ax.set_axis_off()
            self.breakdown_canvas.draw()
            return

        x = df['date']
        width = max(0.6, (x.iloc[-1] - x.iloc[0]).days / len(df) * 0.4) if len(df) > 1 else 0.6

        if has_new and has_unfo:
            bars_new = ax.bar(x, df[new_col].fillna(0), width, color=CHART_COLORS[0], alpha=0.7, label='新增关注')
            bars_unfo = ax.bar(x, -df[unfo_col].fillna(0), width, color=CHART_COLORS[3], alpha=0.7, label='取消关注')
        if has_net:
            net = df[net_col].fillna(0)
            colors_net = [CHART_COLORS[1] if v >= 0 else CHART_COLORS[3] for v in net]
            ax2 = ax.twinx()
            bars_net = ax2.bar(x, net, width * 0.35, color=colors_net, alpha=0.9, label='净增关注')
            ax2.set_ylabel('净增人数', fontsize=10, color='#888')
            ax2.spines['top'].set_visible(False)
            ax2.tick_params(colors='#888', labelsize=9)
            ax2.axhline(y=0, color='#CCC', linewidth=0.5)

        ax.set_ylabel('人数', fontsize=10, color='#666')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E5E7EB')
        ax.spines['bottom'].set_color('#E5E7EB')
        ax.tick_params(colors='#888', labelsize=9)
        ax.grid(axis='y', alpha=0.3, color='#E5E7EB')
        # Combined legend
        lines1 = (bars_new, bars_unfo) if has_new and has_unfo else ()
        lines2 = (bars_net,) if has_net else ()
        if lines1 or lines2:
            labels = [l.get_label() for l in lines1 + lines2 if hasattr(l, 'get_label')]
            ax.legend(lines1 + lines2, labels, fontsize=8, loc='upper left')
        self.breakdown_fig.subplots_adjust(left=0.08, right=0.88, top=0.95, bottom=0.25)
        self.breakdown_canvas.draw()

        # Hover tooltip
        if HAS_MPLCURSORS:
            all_bars = []
            if has_new and has_unfo:
                all_bars.extend([bars_new, bars_unfo])
            if has_net:
                all_bars.append(bars_net)

            for bar_set in all_bars:
                cursor = mplcursors.cursor(bar_set, hover=mplcursors.HoverMode.Transient)
                @cursor.connect("add")
                def on_add(sel):
                    idx = sel.index
                    date_str = x.iloc[idx].strftime('%Y-%m-%d') if idx < len(x) else ''
                    parts = [f" {date_str}"]
                    if has_new and idx < len(df):
                        parts.append(f"新增:{int(df[new_col].iloc[idx]) if pd.notna(df[new_col].iloc[idx]) else '-'}")
                    if has_unfo and idx < len(df):
                        parts.append(f"取消:{int(df[unfo_col].iloc[idx]) if pd.notna(df[unfo_col].iloc[idx]) else '-'}")
                    if has_net and idx < len(df):
                        v = df[net_col].iloc[idx]
                        parts.append(f"净增:{int(v) if pd.notna(v) else '-'}")
                    sel.annotation.set_text('  '.join(parts))
                    sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95, ec="#D1D5DB", lw=0.5)
                    sel.annotation.set_fontsize(9)
                    sel.annotation.set_fontfamily(CJK)
                self._cursors.append(cursor)

    def _draw_accel(self, data):
        """Second derivative: acceleration of daily new followers."""
        self.accel_fig.clear()
        ax = self.accel_fig.add_subplot(111)
        df = data['fans_data'].sort_values('date')
        col = '净增关注人数'
        if col not in df.columns:
            ax.text(0.5, 0.5, '暂无净增数据', ha='center', va='center', fontsize=12, color='#999')
            ax.set_axis_off()
            self.accel_canvas.draw()
            return

        daily = df[col].fillna(0)
        accel = daily.diff().dropna()  # Δ² = change of net-change
        if accel.empty:
            ax.text(0.5, 0.5, '数据不足以计算加速度', ha='center', va='center', fontsize=12, color='#999')
            ax.set_axis_off()
            self.accel_canvas.draw()
            return

        accel_dates = df['date'].iloc[1:]  # align with accel (one less row)
        colors = [CHART_COLORS[1] if v >= 0 else CHART_COLORS[3] for v in accel]
        ax.bar(accel_dates, accel, color=colors, alpha=0.7, width=0.7)
        ax.axhline(y=0, color='#CCC', linewidth=0.5)
        ax.set_ylabel('加速度（Δ²）', fontsize=10, color='#666')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E5E7EB')
        ax.spines['bottom'].set_color('#E5E7EB')
        ax.tick_params(colors='#888', labelsize=9)
        ax.grid(axis='y', alpha=0.3, color='#E5E7EB')
        self.accel_fig.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.25)
        self.accel_canvas.draw()

        if HAS_MPLCURSORS:
            bars = ax.containers[0] if ax.containers else None
            if bars:
                cursor = mplcursors.cursor(bars, hover=mplcursors.HoverMode.Transient)
                @cursor.connect("add")
                def on_add(sel):
                    idx = sel.index
                    if idx < len(accel):
                        ds = accel_dates.iloc[idx].strftime('%Y-%m-%d') if hasattr(accel_dates.iloc[idx], 'strftime') else str(accel_dates.iloc[idx])
                        v = accel.iloc[idx]
                        sel.annotation.set_text(f" {ds}  加速度: {v:+.1f}")
                        sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95, ec="#D1D5DB", lw=0.5)
                        sel.annotation.set_fontsize(9)
                        sel.annotation.set_fontfamily(CJK)
                self._cursors.append(cursor)

    def _clear_cursors(self):
        for c in self._cursors:
            try:
                c.disconnect()
            except Exception:
                pass
        self._cursors.clear()
