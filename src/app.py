"""
Trading Visuel — application desktop Price Action multi-timeframe.

Transforme le notebook 04_signal_price_action.ipynb en logiciel graphique :
  * graphique de chandeliers interactif (bougies, EMA, S/R, Order Blocks,
    FVG, patterns, lignes Entree/SL/TP)
  * panneau synthese du signal multi-timeframe
  * analyse IA (Ollama) avec affichage du rapport dans l'onglet (intra logiciel)

Lancement :
    .venv\\Scripts\\python.exe app.py
"""
import sys

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QComboBox, QPushButton, QSplitter, QTabWidget, QPlainTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QScrollArea,
    QMessageBox, QFrame, QSizePolicy,
)

from lib.price_action import analyze_pair, compute_signal, ask_ai, DEFAULT_TFS, pip_size
from lib.config import PAIRES
from chart_widget import CandleChart

EXTRA_PAIRS = {
    "USDCHF": "USD/CHF",
    "AUDUSD": "AUD/USD",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
}

ACCENT = QColor(66, 165, 245)
DIR_COLORS = {"BUY": QColor(38, 166, 91), "SELL": QColor(239, 83, 80), "HOLD": QColor(255, 167, 38)}


class AnalysisWorker(QThread):
    done = Signal(object, object)
    step = Signal(str)

    def __init__(self, symbol, full_name, tfs, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.full_name = full_name
        self.tfs = tfs

    def run(self):
        try:
            self.step.emit("Téléchargement et analyse des données…")
            result = analyze_pair(self.symbol, self.full_name, self.tfs, verbose=True, compute_signal=False)
            self.done.emit(result, None)
        except Exception as e:
            self.done.emit(None, str(e))


class AIWorker(QThread):
    done = Signal(object, object)

    def __init__(self, yaml_text, parent=None):
        super().__init__(parent)
        self.yaml_text = yaml_text

    def run(self):
        try:
            text = ask_ai(self.yaml_text)
            self.done.emit(text, None)
        except Exception as e:
            self.done.emit(None, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trading Visuel — Price Action Multi-Timeframe")
        self.resize(1440, 860)

        self.result = None
        self._ai_worker = None
        self._worker = None

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)

        # Barre d'outils
        toolbar = QHBoxLayout()
        toolbar.addWidget(self._label("Paire :"))
        self.pair_combo = QComboBox()
        for pair in PAIRES:
            self.pair_combo.addItem(f"{pair}  ({EXTRA_PAIRS.get(pair, pair.replace('USD', '/USD'))})", pair)
        for pair, name in EXTRA_PAIRS.items():
            self.pair_combo.addItem(f"{pair}  ({name})", pair)
        toolbar.addWidget(self.pair_combo)

        toolbar.addSpacing(12)
        toolbar.addWidget(self._label("Graphique :"))
        self.tf_combo = QComboBox()
        self.tf_combo.addItem("M15", "M15")
        self.tf_combo.addItem("H1", "H1")
        self.tf_combo.addItem("Daily", "Daily")
        self.tf_combo.addItem("Weekly", "Weekly")
        toolbar.addWidget(self.tf_combo)
        self.tf_combo.currentIndexChanged.connect(self._on_tf_changed)

        toolbar.addStretch(1)
        self.btn_analyze = QPushButton("Analyser")
        self.btn_analyze.setStyleSheet(
            f"QPushButton {{ background-color: {ACCENT.name()}; color: white; font-weight: bold;"
            "padding: 7px 18px; border: none; border-radius: 5px; }}"
            "QPushButton:hover { background-color: #1e88e5; }")
        self.btn_analyze.clicked.connect(self._run_analysis)
        toolbar.addWidget(self.btn_analyze)

        root.addLayout(toolbar)

        # Contenu principal
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_header = QLabel("Sélectionnez une paire puis cliquez sur Analyser.")
        self.chart_header.setStyleSheet("font-weight: bold; padding: 4px;")
        left_layout.addWidget(self.chart_header)
        self.chart = CandleChart()
        self.chart.infoChanged.connect(lambda s: None)
        left_layout.addWidget(self.chart, 1)
        hint = QLabel("Molette : zoom   |   Glisser : décaler   |   Clic droit : réinitialiser")
        hint.setStyleSheet("color: #8c96aa; font-size: 10px; padding-left: 4px;")
        left_layout.addWidget(hint)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.signal_tab = QWidget()
        self.tabs.addTab(self.signal_tab, "Signal")
        self.ai_tab = QWidget()
        self.tabs.addTab(self.ai_tab, "Analyse IA")
        self._build_ai_tab()
        right_layout.addWidget(self.tabs)
        right.setMaximumWidth(520)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter, 1)

        self.status = QLabel("Prêt.")
        self.status.setStyleSheet("color: #8c96aa; padding: 2px;")
        root.addWidget(self.status)

        self.setCentralWidget(central)
        self.refresh_signal_tab()

    def _label(self, text, bold=False):
        lbl = QLabel(text)
        if bold:
            lbl.setStyleSheet("font-weight: bold;")
        return lbl

    def _build_ai_tab(self):
        v = QVBoxLayout(self.ai_tab)
        v.setContentsMargins(0, 0, 0, 0)

        hint = QLabel("Envoie le signal YAML à Ollama (modèle gemma4) pour une analyse Price Action "
                      "en langage naturel.\nAssurez-vous que Ollama tourne : `ollama serve`.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8c96aa;")
        v.addWidget(hint)

        frame = QFrame()
        frame.setStyleSheet("QFrame { border: 1px solid #2a3242; border-radius: 6px; }")
        fv = QVBoxLayout(frame)
        fv.setContentsMargins(6, 6, 6, 6)
        self.ai_editor = QPlainTextEdit()
        self.ai_editor.setReadOnly(True)
        self.ai_editor.setFrameShape(QFrame.NoFrame)
        self.ai_editor.setPlaceholderText("Le rapport de l'analyse IA apparaîtra ici.")
        fv.addWidget(self.ai_editor, 1)
        v.addWidget(frame, 1)

        self.btn_ai_in_tab = QPushButton("Générer l'analyse IA")
        self.btn_ai_in_tab.setEnabled(False)
        self.btn_ai_in_tab.clicked.connect(self._run_ai)
        v.addWidget(self.btn_ai_in_tab)

    # ------------------------------------------------------------ actions
    def _selected_pair(self):
        return self.pair_combo.currentData()

    def _run_analysis(self):
        if self._worker and self._worker.isRunning():
            return
        symbol = self._selected_pair()
        self.btn_analyze.setEnabled(False)
        self.btn_ai_in_tab.setEnabled(False)
        self.status.setText(f"Analyse de {symbol}…")
        self._worker = AnalysisWorker(symbol, self._full_name(symbol), DEFAULT_TFS)
        self._worker.step.connect(self.status.setText)
        self._worker.done.connect(self._on_analysis_done)
        self._worker.start()

    def _on_analysis_done(self, result, error):
        self.btn_analyze.setEnabled(True)
        if error:
            self.status.setText("Échec de l'analyse.")
            QMessageBox.critical(self, "Erreur", f"L'analyse a échoué :\n{error}")
            return
        self.result = result
        self.chart.set_result(result)
        self._refresh_header()
        self.refresh_signal_tab()
        self.btn_ai_in_tab.setEnabled(False)
        self.ai_editor.clear()
        self.status.setText(
            f"{result['symbol']} analysé — graphique prêt. Cliquez sur « Générer le signal ».")

    def _generate_signal(self):
        if not self.result or "score" in self.result:
            return
        self.status.setText("Génération du signal…")
        self.result.update(compute_signal(self.result))
        self.chart.set_result(self.result)
        self.btn_ai_in_tab.setEnabled(True)
        self.ai_editor.clear()
        self.refresh_signal_tab()
        s = self.result["score"]
        self.status.setText(
            f"Signal {s['direction']} (confiance {s['confidence']}%) — {self.result['symbol']}")

    def _run_ai(self):
        if not self.result or "yaml_text" not in self.result:
            return
        if self._ai_worker and self._ai_worker.isRunning():
            return
        self.btn_ai_in_tab.setEnabled(False)
        self.status.setText("Appel à Ollama… (cela peut prendre ~30 s)")
        self.ai_editor.setPlainText("Analyse IA en cours. Veuillez patienter…")
        self._ai_worker = AIWorker(self.result["yaml_text"])
        self._ai_worker.done.connect(self._on_ai_done)
        self._ai_worker.start()

    def _on_ai_done(self, text, error):
        self.btn_ai_in_tab.setEnabled(True)
        self.tabs.setCurrentIndex(1)
        if error:
            self.status.setText("Analyse IA : échec.")
            self.ai_editor.setPlainText(f"Erreur : {error}")
            return
        self.ai_editor.setPlainText(text)
        first_line = text.splitlines()[0] if text else ""
        self.status.setText(f"Analyse IA terminée ({first_line})")

    def _on_tf_changed(self):
        if self.result:
            self.chart.set_tf(self.tf_combo.currentData())
            self._refresh_header()

    def _refresh_header(self):
        tf = self.tf_combo.currentData()
        inter = self.result["tfs"][tf]["interval"]
        per = self.result["tfs"][tf]["period"]
        self.chart_header.setText(
            f"{self.result['symbol']} ({self.result['full_name']}) — {tf}  (intervalle {inter} / {per})")

    def _full_name(self, symbol):
        return EXTRA_PAIRS.get(symbol, symbol.replace("USD", "/USD"))

    # ------------------------------------------------------- panneau signal
    def refresh_signal_tab(self):
        container = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setSpacing(6)

        has_data = self.result is not None
        has_signal = has_data and "score" in self.result

        if not has_signal:
            hint = QLabel("Analysez le graphique avec le bouton « Analyser », puis cliquez sur "
                          "« Générer le signal » pour obtenir la synthèse multi-timeframe, "
                          "les zones d'entrée et le signal YAML.")
            hint.setWordWrap(True)
            hint.setStyleSheet("color: #8c96aa;")
            lay.addWidget(hint)
            lay.addStretch(1)
            scroll.setWidget(body)
            self._finish_signal_tab(container, scroll)
            return

        r = self.result
        pip = pip_size(r["symbol"])
        dec = 3 if "JPY" in r["symbol"] else 5
        pf = f".{dec}f"

        # --- Synthèse
        s = r["score"]
        color = DIR_COLORS[s["direction"]]
        head = QLabel()
        head.setAlignment(Qt.AlignCenter)
        head.setStyleSheet(
            f"border: 2px solid {color.name()}; border-radius: 8px; font-size: 18px;"
            f"font-weight: bold; color: {color.name()}; padding: 10px;")
        head.setText(
            f"{s['direction']}   {s['confidence']}%  ({s['strength'] or '—'})\n"
            f"Biais bull {s['bull_pct']}% / bear {s['bear_pct']}%   ·   Confluence {s['confluence']}")
        lay.addWidget(head)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(s["confidence"])
        bar.setFormat(f"Confiance : {s['confidence']}%")
        bar.setStyleSheet(
            f"QProgressBar {{ border: 1px solid #2a3242; border-radius: 4px; height: 16px; background: #141a26; }}"
            f"QProgressBar::chunk {{ background-color: {color.name()}; border-radius: 4px; }}")
        lay.addWidget(bar)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.addRow("Prix actuel", self._v(f"{r['price']:{pf}}  (spread 0.8)"))
        form.addRow("Session", self._v(r["signal_yaml"]["session"]["name"]))
        e, sl, tp = r["entry"], r["stop_loss"], r["take_profit"]
        ex = f"{e:{pf}}"
        form.addRow("Entrée", self._v(ex if e else "—"))
        form.addRow("Stop Loss", self._v(f"{sl:{pf}}" if sl else "—"))
        form.addRow("Take Profit", self._v(f"{tp:{pf}}" if tp else "—"))
        rr = "—"
        if e and sl and tp:
            rr = f"{abs(tp - e) / abs(e - sl):.2f}"
        form.addRow("Risk / Reward", self._v(rr))
        nses = r["signal_yaml"]["support"]["nearest"]
        nres = r["signal_yaml"]["resistance"]["nearest"]
        sup = f"{nses['price']:{pf}}" if nses["exists"] else "—"
        sup += f"  ({nses['distance_pips']} pips, {nses['strength']})" if nses["exists"] else ""
        res = f"{nres['price']:{pf}}" if nres["exists"] else "—"
        res += f"  ({nres['distance_pips']} pips, {nres['strength']})" if nres["exists"] else ""
        form.addRow("Support proche", self._v(sup))
        form.addRow("Résistance proche", self._v(res))
        form.addRow("Zones d'achat", self._v(", ".join(f"{z:{pf}}" for z in r["buy_zone"]) or "—"))
        form.addRow("Zones de vente", self._v(", ".join(f"{z:{pf}}" for z in r["sell_zone"]) or "—"))
        form.addRow("Volatilité", self._v(r["volatility"]))
        vol = r["volume_info"]
        vol_txt = f"{vol['trend']}" + (f" (dernier : {vol['tick_volume']})" if vol["tick_volume"] else "")
        form.addRow("Volume", self._v(vol_txt if vol["available"] else "N/D"))
        liq = r["liquidity"]
        liquid_txt = (f"liquidité au-dessus {'✓' if liq['liquidity_above'] else '✗'}, "
                      f"en dessous {'✓' if liq['liquidity_below'] else '✗'}"
                      f"   (sweep haut {'✓' if liq['sweep_above'] else '✗'}, "
                      f"bas {'✓' if liq['sweep_below'] else '✗'})")
        form.addRow("Liquidité", self._v(liquid_txt))
        lay.addLayout(form)

        # --- Raisons / confluences
        lay.addWidget(self._section("Raisons"))
        for reason in s["reasons"]:
            lay.addWidget(QLabel("· " + reason))

        # --- EMA
        lay.addWidget(self._section("EMAs"))
        eform = QFormLayout()
        for tf in ("Daily", "H1"):
            ema = r["ema_data"].get(tf, {})
            eform.addRow(f"{tf} — alignement", self._v(f"{ema.get('alignment', '—')}  /  {ema.get('price_position', '—')}"))
        lay.addLayout(eform)

        # --- Tableau multi-timeframe
        lay.addWidget(self._section("Multi-timeframe"))
        table = QTableWidget()
        tfs_ordered = list(r["tfs"].keys())
        table.setRowCount(len(tfs_ordered))
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(["TF", "Intervalle", "Structure", "Tendance", "Score", "RSI / ADX"])
        hh = table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.Stretch)
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        for row, tf in enumerate(tfs_ordered):
            ind = r["indicators"][tf]
            tr = r["trend"][tf]
            last = ind.iloc[-1]
            vals = [
                tf, r["tfs"][tf]["interval"], r["structure"][tf],
                f"{tr['direction']} ({tr['strength'] or '—'})", f"{tr['score']:+.1f}",
                f"{last['rsi']:.0f} / {last['adx']:.0f}",
            ]
            for col, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if col == 3:
                    d = tr["direction"]
                    item.setForeground(DIR_COLORS["BUY" if d == "Bullish" else "SELL" if d == "Bearish" else "HOLD"])
                table.setItem(row, col, item)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setFixedHeight(table.sizeHint().height() + 8)
        lay.addWidget(table)

        # --- Patterns récents
        lay.addWidget(self._section("Patterns récents (M15)"))
        if r["patterns"]:
            for p_ in r["patterns"]:
                lay.addWidget(QLabel(f"· bougie {p_['candle']:+d} : {p_['pattern']} ({p_['signal']})"))
        else:
            lay.addWidget(QLabel("Aucun pattern détecté sur les 10 dernières bougies M15."))

        lay.addStretch(1)
        scroll.setWidget(body)
        self._finish_signal_tab(container, scroll)

    def _finish_signal_tab(self, container, scroll):
        v = QVBoxLayout(container)
        v.setContentsMargins(0, 0, 0, 0)

        hint = QLabel("Synthèse du signal multi-timeframe : score, confluence, zones d'entrée, "
                      "supports/résistances, liquidité et signal YAML.\n"
                      "Générez le signal après avoir analysé le graphique avec « Analyser ».")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #8c96aa;")
        v.addWidget(hint)

        frame = QFrame()
        frame.setStyleSheet("QFrame { border: 1px solid #2a3242; border-radius: 6px; }")
        fv = QVBoxLayout(frame)
        fv.setContentsMargins(6, 6, 6, 6)
        fv.addWidget(scroll)
        v.addWidget(frame, 1)

        has_data = self.result is not None
        has_signal = has_data and "score" in self.result
        self.btn_signal = QPushButton("Générer le signal")
        self.btn_signal.setEnabled(has_data and not has_signal)
        self.btn_signal.clicked.connect(self._generate_signal)
        v.addWidget(self.btn_signal)
        self._replace_signal_tab(container)

    def _replace_signal_tab(self, scroll):
        current = self.tabs.currentIndex()
        old = self.signal_tab
        self.tabs.removeTab(0)
        self.tabs.insertTab(0, scroll, "Signal")
        self.tabs.setCurrentIndex(current)
        old.deleteLater()

    def _section(self, title):
        lbl = QLabel(title)
        lbl.setStyleSheet(
            "font-weight: bold; color: " + ACCENT.name() + ";"
            "border-bottom: 1px solid #2a3242; padding-bottom: 2px; margin-top: 8px;")
        return lbl

    def _v(self, text):
        lbl = QLabel(str(text))
        lbl.setWordWrap(True)
        return lbl


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()