"""
阅读量分析页面 — 每日趋势、渠道分布、文章排行。全中文。
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
    'warning': '#F59E0B', 'danger': '#EF4444', 'bg': '#F0F2F5',
}
CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#F97316', '#6366F1']

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


class ReadOverviewPage(QWidget):
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
        self.current_range = 'all'
        self.range_btns = {}
        self._cursors = []
        self._init_ui()

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
        self.kpi_total = _make_kpi("总阅读量", "—", self.colors['primary'], self.colors)
        self.kpi_avg = _make_kpi("日均阅读", "—", self.colors['success'], self.colors)
        self.kpi_peak = _make_kpi("峰值阅读", "—", self.colors['warning'], self.colors)
        self.kpi_share = _make_kpi("总分享数", "—", '#8B5CF6', self.colors)
        kpi_layout.addWidget(self.kpi_total)
        kpi_layout.addWidget(self.kpi_avg)
        kpi_layout.addWidget(self.kpi_peak)
        kpi_layout.addWidget(self.kpi_share)
        layout.addLayout(kpi_layout)

        # === Trend Chart ===
        trend_card = _make_card(self.colors)
        tl = QVBoxLayout(trend_card)
        tl.setContentsMargins(16, 12, 16, 8)
        trend_title = QLabel("每日阅读趋势")
        trend_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        tl.addWidget(trend_title)
        self.trend_fig = Figure(figsize=(8, 3), dpi=100, facecolor='white')
        self.trend_canvas = FigureCanvas(self.trend_fig)
        self.trend_canvas.setStyleSheet("background: white;")
        tl.addWidget(self.trend_canvas)
        layout.addWidget(trend_card)

        # === Bottom: Channel + Articles ===
        bottom = QHBoxLayout()
        bottom.setSpacing(16)

        ch_card = _make_card(self.colors)
        cl = QVBoxLayout(ch_card)
        cl.setContentsMargins(16, 12, 16, 8)
        ch_title = QLabel("渠道来源分布")
        ch_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        cl.addWidget(ch_title)
        self.channel_fig = Figure(figsize=(4, 3.5), dpi=100, facecolor='white')
        self.channel_canvas = FigureCanvas(self.channel_fig)
        self.channel_canvas.setStyleSheet("background: white;")
        cl.addWidget(self.channel_canvas)
        bottom.addWidget(ch_card, 1)

        art_card = _make_card(self.colors)
        al = QVBoxLayout(art_card)
        al.setContentsMargins(16, 12, 16, 8)
        art_title = QLabel("文章阅读排行 TOP10")
        art_title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {self.colors['text_dark']}; border: none; font-family: '{CJK}';")
        al.addWidget(art_title)
        self.article_fig = Figure(figsize=(5, 3.5), dpi=100, facecolor='white')
        self.article_canvas = FigureCanvas(self.article_fig)
        self.article_canvas.setStyleSheet("background: white;")
        al.addWidget(self.article_canvas)
        bottom.addWidget(art_card, 1)

        layout.addLayout(bottom)
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
        if not data:
            return {}
        start, end = self._get_date_range()
        if start is None:
            return data

        result = {}
        for key, df in data.items():
            if 'date' in df.columns:
                dates = pd.to_datetime(df['date'], errors='coerce')
                mask = (dates >= start) & (dates <= end)
                filtered = df[mask].copy()
                if not filtered.empty:
                    result[key] = filtered
            else:
                result[key] = df
        return result

    # === Data Update ===

    def update_data(self, data):
        self.data = data
        self._refresh_all()

    def _refresh_all(self):
        data = self._filter_data(self.data)
        if not data:
            self._show_empty()
            return
        self._update_kpis(data)
        self._draw_trend(data)
        self._draw_channel(data)
        self._draw_articles(data)

    def _show_empty(self):
        self._set_kpi(self.kpi_total, "—")
        self._set_kpi(self.kpi_avg, "—")
        self._set_kpi(self.kpi_peak, "—")
        self._set_kpi(self.kpi_share, "—")
        for fig, canvas in [
            (self.trend_fig, self.trend_canvas),
            (self.channel_fig, self.channel_canvas),
            (self.article_fig, self.article_canvas),
        ]:
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, '所选时间段内暂无数据',
                    ha='center', va='center', fontsize=14, color='#999',
                    fontfamily=CJK)
            ax.set_axis_off()
            canvas.draw()
        self._cursors.clear()

    # === KPIs ===

    def _update_kpis(self, data):
        if 'daily_by_channel' in data:
            df = data['daily_by_channel']
            total_df = df[df['channel'] == '全部']
            if not total_df.empty:
                total = total_df['readers'].sum()
                avg = total_df['readers'].mean()
                peak = total_df['readers'].max()
                self._set_kpi(self.kpi_total, f"{total:,}")
                self._set_kpi(self.kpi_avg, f"{avg:,.0f}")
                self._set_kpi(self.kpi_peak, f"{peak:,}")
        if 'daily_summary' in data:
            df = data['daily_summary']
            self._set_kpi(self.kpi_share, f"{df['shares'].sum():,}")

    def _set_kpi(self, card, value):
        lbl = card.findChild(QLabel, "kpi_value")
        if lbl:
            lbl.setText(value)

    # === Charts ===

    def _draw_trend(self, data):
        self._clear_cursors()
        self.trend_fig.clear()
        ax = self.trend_fig.add_subplot(111)
        if 'daily_by_channel' not in data:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='#999')
            self.trend_canvas.draw()
            return

        df = data['daily_by_channel']
        total_df = df[df['channel'] == '全部'].copy()
        if total_df.empty:
            total_df = df.groupby('date')['readers'].sum().reset_index()
            total_df.columns = ['date', 'readers']
        total_df = total_df.sort_values('date')

        ax.fill_between(total_df['date'], total_df['readers'], alpha=0.15, color=CHART_COLORS[0])
        ax.plot(total_df['date'], total_df['readers'], color=CHART_COLORS[0],
                linewidth=2, marker='o', markersize=3, label='阅读人数')
        ax.set_ylabel('阅读人数', fontsize=10, color='#666')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E5E7EB')
        ax.spines['bottom'].set_color('#E5E7EB')
        ax.tick_params(colors='#888', labelsize=9)
        ax.grid(axis='y', alpha=0.3, color='#E5E7EB')
        self.trend_fig.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.25)
        self.trend_canvas.draw()

        # Hover tooltip — only on data points, not on line segments
        if HAS_MPLCURSORS:
            # Prepare detailed summary data for tooltips
            summary_df = None
            if 'daily_summary' in data:
                summary_df = data['daily_summary'][['date', 'shares', 'clicks', 'favorites']].copy()
                summary_df['date'] = pd.to_datetime(summary_df['date'])

            scatter = ax.scatter(total_df['date'], total_df['readers'],
                                 s=20, color=CHART_COLORS[0], zorder=5)
            cursor = mplcursors.cursor(scatter, hover=mplcursors.HoverMode.Transient)
            @cursor.connect("add")
            def on_add(sel):
                idx = sel.index
                row = total_df.iloc[idx]
                date_str = row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date'])
                text = f" {date_str}  阅读: {int(row['readers']):,} "
                if summary_df is not None:
                    match = summary_df[summary_df['date'].dt.strftime('%Y-%m-%d') == date_str]
                    if not match.empty:
                        r = match.iloc[0]
                        shares = int(r['shares']) if pd.notna(r['shares']) else 0
                        clicks = int(r['clicks']) if pd.notna(r['clicks']) else 0
                        faves = int(r['favorites']) if pd.notna(r['favorites']) else 0
                        text += f"\n  分享: {shares:,}  在看: {clicks:,}  收藏: {faves:,} "
                sel.annotation.set_text(text)
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95, ec="#D1D5DB", lw=0.5)
                sel.annotation.set_fontsize(9)
                sel.annotation.set_fontfamily(CJK)
            self._cursors.append(cursor)

    def _draw_channel(self, data):
        self.channel_fig.clear()
        ax = self.channel_fig.add_subplot(111)
        if 'daily_by_channel' not in data:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='#999')
            self.channel_canvas.draw()
            return

        df = data['daily_by_channel']
        ch_sum = df[df['channel'] != '全部'].groupby('channel')['readers'].sum().sort_values(ascending=False)
        if ch_sum.empty:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='#999')
            self.channel_canvas.draw()
            return

        wedges, texts, autotexts = ax.pie(
            ch_sum.values, labels=None,
            colors=CHART_COLORS[:len(ch_sum)],
            autopct='%1.1f%%', pctdistance=0.75,
            startangle=90, wedgeprops=dict(width=0.45, edgecolor='white', linewidth=2)
        )
        for t in autotexts:
            t.set_fontsize(8)
            t.set_color('white')
        # Legend instead of inline labels to avoid overlap
        ax.legend(wedges, ch_sum.index, loc='upper left', fontsize=8,
                  bbox_to_anchor=(-0.1, 1.05), framealpha=0.9, edgecolor='#E5E7EB')
        self.channel_fig.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.05)
        self.channel_canvas.draw()

        # Hover tooltip
        if HAS_MPLCURSORS and wedges:
            cursor = mplcursors.cursor(wedges, hover=mplcursors.HoverMode.Transient)
            @cursor.connect("add")
            def on_add(sel):
                idx = list(wedges).index(sel.artist)
                label = ch_sum.index[idx]
                value = ch_sum.values[idx]
                total = ch_sum.sum()
                pct = value / total * 100
                sel.annotation.set_text(f" {label}  {value:,} ({pct:.1f}%) ")
                sel.annotation.get_bbox_patch().set(fc="white", alpha=0.95, ec="#D1D5DB", lw=0.5)
                sel.annotation.set_fontsize(9)
                sel.annotation.set_fontfamily(CJK)
            self._cursors.append(cursor)

    def _draw_articles(self, data):
        self.article_fig.clear()
        ax = self.article_fig.add_subplot(111)
        if 'article_ranking' not in data:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='#999')
            self.article_canvas.draw()
            return

        df = data['article_ranking']
        ranking = df.groupby('title')['readers'].max().sort_values(ascending=True).tail(10)
        if ranking.empty:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14, color='#999')
            self.article_canvas.draw()
            return

        labels = [t[:16] + '...' if len(t) > 16 else t for t in ranking.index]
        colors_bar = [CHART_COLORS[0] if i < len(ranking) - 3 else CHART_COLORS[1] for i in range(len(ranking))]
        bars = ax.barh(labels, ranking.values, color=colors_bar, height=0.6, edgecolor='none')
        ax.set_xlabel('阅读人数', fontsize=10, color='#666')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E5E7EB')
        ax.spines['bottom'].set_color('#E5E7EB')
        ax.tick_params(colors='#888', labelsize=8)
        for i, v in enumerate(ranking.values):
            ax.text(v + max(ranking.values) * 0.01, i, f'{v:,}', va='center', fontsize=8, color='#555')
        self.article_fig.subplots_adjust(left=0.35, right=0.92, top=0.95, bottom=0.15)
        self.article_canvas.draw()

        # Hover tooltip
        if HAS_MPLCURSORS and bars:
            cursor = mplcursors.cursor(bars, hover=mplcursors.HoverMode.Transient)
            @cursor.connect("add")
            def on_add(sel):
                idx = list(bars).index(sel.artist)
                full_title = ranking.index[idx]
                value = ranking.values[idx]
                sel.annotation.set_text(f" {full_title}  阅读: {value:,} ")
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
