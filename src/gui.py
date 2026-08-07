import wx
import time
import os
import configparser
import ctypes
from audio import play_click
from input_win32 import NUMPAD_DUAL_MAP
from scroller import AutoScroller

APP_NAME = "Compasero"
APP_VERSION = "1.0"
APP_TITLE = f"{APP_NAME} v{APP_VERSION} - Secuenciador de Letras por Compases"

config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

HOTKEY_ID_BASE_TOGGLE = 1000
HOTKEY_ID_BASE_STOP = 2000
HOTKEY_ID_BASE_TAP_TRIGGER = 3000

def ensure_default_templates_exist():
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guiones")
    os.makedirs(base_dir, exist_ok=True)
    
    chacarera_path = os.path.join(base_dir, "Chacarera_Estructura.txt")
    if not os.path.exists(chacarera_path):
        with open(chacarera_path, 'w', encoding='utf-8') as f:
            f.write("# Plantilla de Guion: Chacarera Tradicional\nBPM: 140\nTIEMPOS_COMPAS: 6\nDISPAROS: 1, 4\nREPOSO: 1\n\nsilencio: 8\nbajar: 8\nsilencio: 8\nbajar: 8\nsilencio: 4\n")

    zamba_path = os.path.join(base_dir, "Zamba_Estructura.txt")
    if not os.path.exists(zamba_path):
        with open(zamba_path, 'w', encoding='utf-8') as f:
            f.write("# Plantilla de Guion: Zamba Tradicional\nBPM: 72\nTIEMPOS_COMPAS: 6\nDISPAROS: 1\nREPOSO: 1\n\nsilencio: 8\nbajar: 12\nsilencio: 4\nbajar: 12\nsilencio: 4\n")

    balada_path = os.path.join(base_dir, "Balada_Rock_4-4.txt")
    if not os.path.exists(balada_path):
        with open(balada_path, 'w', encoding='utf-8') as f:
            f.write("# Plantilla de Guion: Balada / Rock 4/4 Standard\nBPM: 100\nTIEMPOS_COMPAS: 4\nDISPAROS: 1\nREPOSO: 1\n\nsilencio: 4\nbajar: 8\nsilencio: 4\nbajar: 8\nsilencio: 8\nbajar: 8\nsilencio: 4\n")

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title=APP_TITLE, size=(850, 750))
        
        ensure_default_templates_exist()
        
        self.scroller = AutoScroller(log_callback=self.update_status_log)
        self.registered_ids = []
        self.tap_times = []
        self.is_tap_session_active = False
        self.load_config()
        self.capturing_target = None
        
        panel = wx.Panel(self)
        self.panel = panel
        main_vbox = wx.BoxSizer(wx.VERTICAL)
        
        # --- PESTAÑAS (wx.Notebook) ---
        self.notebook = wx.Notebook(panel)
        
        # Pestaña Modo Simple
        self.tab_inicio = wx.Panel(self.notebook)
        self.init_tab_inicio(self.tab_inicio)
        self.notebook.AddPage(self.tab_inicio, "Modo Simple")
        
        # Pestaña Atajos
        self.tab_atajos = wx.Panel(self.notebook)
        self.init_tab_atajos(self.tab_atajos)
        self.notebook.AddPage(self.tab_atajos, "Atajos de Teclado")
        
        # Pestaña Guion Avanzado
        self.tab_guion = wx.Panel(self.notebook)
        self.init_tab_guion(self.tab_guion)
        self.notebook.AddPage(self.tab_guion, "Guion Avanzado")
        
        main_vbox.Add(self.notebook, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        
        # --- LOG / ESTADO COMPARTIDO ABAJO ---
        main_vbox.Add(wx.StaticText(panel, label="Estado actual:"), flag=wx.LEFT | wx.RIGHT, border=10)
        self.txt_log = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 70))
        main_vbox.Add(self.txt_log, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        panel.SetSizer(main_vbox)
        
        panel.Bind(wx.EVT_CHAR_HOOK, self.on_key_hook)
        
        self.setup_global_hotkeys()
        self.Show()

    # --- DISEÑO PESTAÑA MODO SIMPLE ---
    def init_tab_inicio(self, tab):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        vbox.Add(wx.StaticText(tab, label=f"Bienvenido a {APP_NAME} v{APP_VERSION}: Configuración maestro de ritmos y compases."), flag=wx.ALL, border=10)
        
        box_tap = wx.StaticBox(tab, label="Configuración del Modo Simple")
        sizer_tap = wx.StaticBoxSizer(box_tap, wx.VERTICAL)
        
        row_tap1 = wx.BoxSizer(wx.HORIZONTAL)
        row_tap1.Add(wx.StaticText(tab, label="Tiempos por compás:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_tiempos = wx.SpinCtrl(tab, value=str(self.scroller.simple_beats_per_line), min=1, max=9999, size=(75, -1))
        self.spin_tiempos.Bind(wx.EVT_SPINCTRL, self.on_simple_beats_change)
        row_tap1.Add(self.spin_tiempos, flag=wx.RIGHT, border=15)
        
        row_tap1.Add(wx.StaticText(tab, label="Velocidad (BPM):"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_bpm = wx.SpinCtrl(tab, value=str(self.scroller.simple_bpm), min=30, max=999, size=(65, -1))
        self.spin_bpm.Bind(wx.EVT_SPINCTRL, self.on_simple_bpm_change)
        row_tap1.Add(self.spin_bpm, flag=wx.RIGHT, border=15)
        
        row_tap1.Add(wx.StaticText(tab, label="Compases de reposo:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_simple_reposo = wx.SpinCtrl(tab, value=str(self.scroller.simple_lead_in_bars), min=0, max=9999, size=(75, -1))
        self.spin_simple_reposo.Bind(wx.EVT_SPINCTRL, self.on_simple_reposo_change)
        row_tap1.Add(self.spin_simple_reposo, flag=wx.RIGHT, border=15)
        
        self.btn_tap = wx.Button(tab, label=f"Calibrar Ritmo (O presiona {self.tecla_call_tap})")
        self.btn_tap.Bind(wx.EVT_BUTTON, lambda e: self.on_tap_trigger())
        row_tap1.Add(self.btn_tap)
        
        sizer_tap.Add(row_tap1, flag=wx.EXPAND | wx.ALL, border=5)
        
        sizer_tap.Add(wx.StaticText(tab, label="Avanzar letra en los tiempos del compás (marcar uno o varios):"), flag=wx.LEFT | wx.TOP, border=5)
        
        self.chk_disparo_list = wx.CheckListBox(tab, choices=[], size=(-1, 80))
        self.update_simple_disparo_choices()
        self.chk_disparo_list.Bind(wx.EVT_CHECKLISTBOX, self.on_simple_disparo_check_toggle)
        sizer_tap.Add(self.chk_disparo_list, flag=wx.EXPAND | wx.ALL, border=5)
        
        self.chk_metronomo_sound = wx.CheckBox(tab, label="Reproducir sonido de metrónomo")
        self.chk_metronomo_sound.SetValue(self.scroller.enable_metronome_sound)
        self.chk_metronomo_sound.Bind(wx.EVT_CHECKBOX, self.on_metronome_sound_toggle)
        sizer_tap.Add(self.chk_metronomo_sound, flag=wx.LEFT | wx.BOTTOM, border=5)
        
        self.lbl_bpm_info = wx.StaticText(tab, label=f"Modo Simple: {self.scroller.simple_bpm} BPM | {self.scroller.simple_beats_per_line} tiempos por compás | {self.scroller.simple_lead_in_bars} compás(es) reposo.")
        sizer_tap.Add(self.lbl_bpm_info, flag=wx.LEFT | wx.BOTTOM, border=5)
        
        vbox.Add(sizer_tap, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        self.btn_iniciar_simple = wx.Button(tab, label=f"INICIAR / PAUSAR (O presiona {self.tecla_toggle})", size=(-1, 50))
        self.btn_iniciar_simple.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.btn_iniciar_simple.Bind(wx.EVT_BUTTON, lambda e: self.scroller.start_or_pause())
        vbox.Add(self.btn_iniciar_simple, flag=wx.EXPAND | wx.ALL, border=10)
        
        tab.SetSizer(vbox)

    def on_simple_bpm_change(self, event):
        val = self.spin_bpm.GetValue()
        self.scroller.simple_bpm = val
        self.update_simple_bpm_label()

    def on_simple_reposo_change(self, event):
        val = self.spin_simple_reposo.GetValue()
        self.scroller.simple_lead_in_bars = val
        self.update_simple_bpm_label()
        self.save_config()

    def update_simple_bpm_label(self):
        self.lbl_bpm_info.SetLabel(f"Modo Simple: {self.scroller.simple_bpm} BPM | {self.scroller.simple_beats_per_line} tiempos por compás | {self.scroller.simple_lead_in_bars} compás(es) reposo.")

    def on_tap_trigger(self):
        now = time.time()
        active_beats = self.scroller.script_beats_per_line if self.scroller.mode == "guion" else self.scroller.simple_beats_per_line
        req_taps = active_beats
        
        if self.tap_times and (now - self.tap_times[-1] > 3.0):
            self.tap_times.clear()
            self.is_tap_session_active = False

        if not self.is_tap_session_active:
            self.is_tap_session_active = True
            self.tap_times = [now]
            self.btn_tap.SetLabel(f"CALIBRANDO (1/{req_taps})...")
            self.lbl_bpm_info.SetLabel(f"Calibrando Ritmo: Toque 1 de {req_taps} registrado.")
            play_click(is_accent=True, enable_sound=self.scroller.enable_metronome_sound)
        else:
            self.tap_times.append(now)
            count = len(self.tap_times)
            
            if count < req_taps:
                self.btn_tap.SetLabel(f"CALIBRANDO ({count}/{req_taps})...")
                self.lbl_bpm_info.SetLabel(f"Calibrando Ritmo: Toque {count} de {req_taps}.")
                play_click(is_accent=False, enable_sound=self.scroller.enable_metronome_sound)
            else:
                deltas = [self.tap_times[i] - self.tap_times[i-1] for i in range(1, req_taps)]
                avg_delta = sum(deltas) / len(deltas)
                bpm = int(60.0 / avg_delta)
                
                if self.scroller.mode == "guion":
                    self.scroller.script_bpm = bpm
                    if hasattr(self, 'spin_script_bpm'): self.spin_script_bpm.SetValue(bpm)
                else:
                    self.scroller.simple_bpm = bpm
                    self.spin_bpm.SetValue(bpm)
                    self.update_simple_bpm_label()
                
                self.update_status_log(f"[RITMO] Metrónomo: {bpm} BPM.")
                
                self.is_tap_session_active = False
                self.tap_times.clear()
                self.btn_tap.SetLabel(f"Calibrar Ritmo (O presiona {self.tecla_call_tap})")
                
                play_click(is_accent=True, enable_sound=self.scroller.enable_metronome_sound)

    def update_simple_disparo_choices(self):
        num_beats = self.scroller.simple_beats_per_line
        choices = [f"Tiempo {i+1}" for i in range(num_beats)]
        self.chk_disparo_list.Set(choices)
        
        valid_beats = set()
        for b in self.scroller.simple_advance_beats:
            if b < num_beats:
                self.chk_disparo_list.Check(b, True)
                valid_beats.add(b)
                
        if not valid_beats:
            valid_beats = {0}
            self.chk_disparo_list.Check(0, True)
            
        self.scroller.simple_advance_beats = valid_beats

    def on_simple_disparo_check_toggle(self, event=None):
        checked_indices = set(self.chk_disparo_list.GetCheckedItems())
        if not checked_indices:
            self.chk_disparo_list.Check(0, True)
            checked_indices = {0}
        self.scroller.simple_advance_beats = checked_indices
        self.save_config()

    def on_simple_beats_change(self, event):
        val = self.spin_tiempos.GetValue()
        self.scroller.simple_beats_per_line = val
        self.update_simple_disparo_choices()
        self.update_simple_bpm_label()

    def on_metronome_sound_toggle(self, event):
        self.scroller.enable_metronome_sound = self.chk_metronomo_sound.IsChecked()

    # --- DISEÑO PESTAÑA ATAJOS ---
    def init_tab_atajos(self, tab):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        box_atajos = wx.StaticBox(tab, label="Personalizar Atajos de Teclado (Capturadora Nativa)")
        sizer_atajos = wx.StaticBoxSizer(box_atajos, wx.VERTICAL)
        
        row1 = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_tecla_toggle = wx.StaticText(tab, label=f"Iniciar/Pausar: [{self.tecla_toggle}]")
        self.btn_cap_toggle = wx.Button(tab, label="Capturar Iniciar/Pausar")
        self.btn_cap_toggle.Bind(wx.EVT_BUTTON, lambda e: self.start_capture('toggle', self.btn_cap_toggle))
        row1.Add(self.lbl_tecla_toggle, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        row1.Add(self.btn_cap_toggle, flag=wx.RIGHT, border=20)
        
        self.lbl_tecla_stop = wx.StaticText(tab, label=f"Reiniciar: [{self.tecla_stop}]")
        self.btn_cap_stop = wx.Button(tab, label="Capturar Reiniciar")
        self.btn_cap_stop.Bind(wx.EVT_BUTTON, lambda e: self.start_capture('stop', self.btn_cap_stop))
        row1.Add(self.lbl_tecla_stop, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        row1.Add(self.btn_cap_stop)
        
        sizer_atajos.Add(row1, flag=wx.EXPAND | wx.BOTTOM, border=10)
        
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.lbl_tecla_avance = wx.StaticText(tab, label=f"Tecla de Avance: [{self.tecla_avance}]")
        self.btn_cap_avance = wx.Button(tab, label="Capturar Tecla de Avance")
        self.btn_cap_avance.Bind(wx.EVT_BUTTON, lambda e: self.start_capture('avance', self.btn_cap_avance))
        row2.Add(self.lbl_tecla_avance, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        row2.Add(self.btn_cap_avance, flag=wx.RIGHT, border=20)
        
        self.lbl_tecla_call_tap = wx.StaticText(tab, label=f"Activar Calibrador Tap: [{self.tecla_call_tap}]")
        self.btn_cap_call_tap = wx.Button(tab, label="Capturar Activar Tap")
        self.btn_cap_call_tap.Bind(wx.EVT_BUTTON, lambda e: self.start_capture('call_tap', self.btn_cap_call_tap))
        row2.Add(self.lbl_tecla_call_tap, flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        row2.Add(self.btn_cap_call_tap)
        
        sizer_atajos.Add(row2, flag=wx.EXPAND | wx.BOTTOM, border=15)
        
        self.btn_reset = wx.Button(tab, label="Restaurar atajos por defecto (+, -, ctrl+alt+t) [O presiona R]")
        self.btn_reset.Bind(wx.EVT_BUTTON, self.on_reset_hotkeys)
        sizer_atajos.Add(self.btn_reset, flag=wx.EXPAND)
        
        vbox.Add(sizer_atajos, flag=wx.EXPAND | wx.ALL, border=10)
        tab.SetSizer(vbox)

    # --- DISEÑO PESTAÑA GUION AVANZADO (TOTALMENTE AUTÓNOMA) ---
    def init_tab_guion(self, tab):
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.chk_usar_guion = wx.CheckBox(tab, label="Activar Modo Guion Avanzado (Estructura personalizada por compases)")
        self.chk_usar_guion.Bind(wx.EVT_CHECKBOX, self.on_guion_mode_toggle)
        vbox.Add(self.chk_usar_guion, flag=wx.ALL, border=10)
        
        box_script_params = wx.StaticBox(tab, label="Configuración Propia del Guion (Autónoma del Modo Simple)")
        sizer_script_params = wx.StaticBoxSizer(box_script_params, wx.VERTICAL)
        
        row_s1 = wx.BoxSizer(wx.HORIZONTAL)
        row_s1.Add(wx.StaticText(tab, label="Tiempos por compás:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_script_tiempos = wx.SpinCtrl(tab, value=str(self.scroller.script_beats_per_line), min=1, max=9999, size=(75, -1))
        self.spin_script_tiempos.Bind(wx.EVT_SPINCTRL, self.on_script_beats_change)
        row_s1.Add(self.spin_script_tiempos, flag=wx.RIGHT, border=15)
        
        row_s1.Add(wx.StaticText(tab, label="Velocidad (BPM):"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_script_bpm = wx.SpinCtrl(tab, value=str(self.scroller.script_bpm), min=30, max=999, size=(65, -1))
        self.spin_script_bpm.Bind(wx.EVT_SPINCTRL, self.on_script_bpm_change)
        row_s1.Add(self.spin_script_bpm, flag=wx.RIGHT, border=15)
        
        row_s1.Add(wx.StaticText(tab, label="Compases de reposo:"), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_script_reposo = wx.SpinCtrl(tab, value=str(self.scroller.script_lead_in_bars), min=0, max=9999, size=(75, -1))
        self.spin_script_reposo.Bind(wx.EVT_SPINCTRL, self.on_script_reposo_change)
        row_s1.Add(self.spin_script_reposo)
        
        sizer_script_params.Add(row_s1, flag=wx.EXPAND | wx.ALL, border=5)
        
        sizer_script_params.Add(wx.StaticText(tab, label="Avanzar letra en los tiempos del compás para este Guion:"), flag=wx.LEFT | wx.TOP, border=5)
        
        self.chk_script_disparo_list = wx.CheckListBox(tab, choices=[], size=(-1, 70))
        self.update_script_disparo_choices()
        self.chk_script_disparo_list.Bind(wx.EVT_CHECKLISTBOX, self.on_script_disparo_check_toggle)
        sizer_script_params.Add(self.chk_script_disparo_list, flag=wx.EXPAND | wx.ALL, border=5)
        
        vbox.Add(sizer_script_params, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        box_builder = wx.StaticBox(tab, label="Agregar Bloque de Canción")
        sizer_builder = wx.StaticBoxSizer(box_builder, wx.VERTICAL)
        
        row_builder1 = wx.BoxSizer(wx.HORIZONTAL)
        self.combo_tipo_bloque = wx.ComboBox(tab, choices=["Bajar Letra (según tiempos marcados)", "Silencio / Instrumental"], style=wx.CB_READONLY)
        self.combo_tipo_bloque.SetSelection(0)
        
        row_builder1.Add(wx.StaticText(tab, label="Tipo: "), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        row_builder1.Add(self.combo_tipo_bloque, flag=wx.RIGHT, border=15)
        
        row_builder1.Add(wx.StaticText(tab, label="Cantidad de Compases: "), flag=wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, border=5)
        self.spin_compases = wx.SpinCtrl(tab, value="8", min=1, max=9999, size=(75, -1))
        row_builder1.Add(self.spin_compases, flag=wx.RIGHT, border=15)
        
        btn_agregar = wx.Button(tab, label="Agregar Bloque")
        btn_agregar.Bind(wx.EVT_BUTTON, self.on_agregar_bloque)
        row_builder1.Add(btn_agregar)
        
        sizer_builder.Add(row_builder1, flag=wx.EXPAND | wx.ALL, border=5)
        vbox.Add(sizer_builder, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        vbox.Add(wx.StaticText(tab, label="Estructura de la Canción (Lista de Bloques por Compases):"), flag=wx.LEFT | wx.RIGHT, border=10)
        
        self.lst_bloques = wx.ListBox(tab, style=wx.LB_SINGLE)
        self.lst_bloques.Bind(wx.EVT_KEY_DOWN, self.on_list_key_down)
        vbox.Add(self.lst_bloques, proportion=1, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, border=10)
        
        hbox_list_ctrl = wx.BoxSizer(wx.HORIZONTAL)
        
        btn_eliminar = wx.Button(tab, label="Eliminar Bloque (Supr)")
        btn_eliminar.Bind(wx.EVT_BUTTON, self.on_eliminar_bloque)
        hbox_list_ctrl.Add(btn_eliminar, flag=wx.RIGHT, border=5)
        
        btn_subir = wx.Button(tab, label="Subir")
        btn_subir.Bind(wx.EVT_BUTTON, self.on_subir_bloque)
        hbox_list_ctrl.Add(btn_subir, flag=wx.RIGHT, border=5)
        
        btn_bajar = wx.Button(tab, label="Bajar")
        btn_bajar.Bind(wx.EVT_BUTTON, self.on_bajar_bloque)
        hbox_list_ctrl.Add(btn_bajar, flag=wx.RIGHT, border=5)
        
        btn_vaciar = wx.Button(tab, label="Vaciar Todo")
        btn_vaciar.Bind(wx.EVT_BUTTON, self.on_vaciar_guion)
        hbox_list_ctrl.Add(btn_vaciar, flag=wx.RIGHT, border=15)
        
        btn_cargar_txt = wx.Button(tab, label="Cargar Guion (.txt)")
        btn_cargar_txt.Bind(wx.EVT_BUTTON, self.on_cargar_guion_txt)
        hbox_list_ctrl.Add(btn_cargar_txt, flag=wx.RIGHT, border=5)
        
        btn_guardar_txt = wx.Button(tab, label="Guardar Guion (.txt)")
        btn_guardar_txt.Bind(wx.EVT_BUTTON, self.on_guardar_guion_txt)
        hbox_list_ctrl.Add(btn_guardar_txt)
        
        vbox.Add(hbox_list_ctrl, flag=wx.ALIGN_CENTER | wx.BOTTOM, border=10)
        
        tab.SetSizer(vbox)

    # --- LÓGICA DE PARÁMETROS PROPIOS DEL GUION ---
    def on_script_bpm_change(self, event):
        self.scroller.script_bpm = self.spin_script_bpm.GetValue()
        self.save_config()

    def on_script_beats_change(self, event):
        self.scroller.script_beats_per_line = self.spin_script_tiempos.GetValue()
        self.update_script_disparo_choices()
        self.save_config()

    def on_script_reposo_change(self, event):
        self.scroller.script_lead_in_bars = self.spin_script_reposo.GetValue()
        self.save_config()

    def update_script_disparo_choices(self):
        num_beats = self.scroller.script_beats_per_line
        choices = [f"Tiempo {i+1}" for i in range(num_beats)]
        self.chk_script_disparo_list.Set(choices)
        
        valid_beats = set()
        for b in self.scroller.script_advance_beats:
            if b < num_beats:
                self.chk_script_disparo_list.Check(b, True)
                valid_beats.add(b)
                
        if not valid_beats:
            valid_beats = {0}
            self.chk_script_disparo_list.Check(0, True)
            
        self.scroller.script_advance_beats = valid_beats

    def on_script_disparo_check_toggle(self, event=None):
        checked_indices = set(self.chk_script_disparo_list.GetCheckedItems())
        if not checked_indices:
            self.chk_script_disparo_list.Check(0, True)
            checked_indices = {0}
        self.scroller.script_advance_beats = checked_indices
        self.save_config()

    def on_cargar_guion_txt(self, event=None):
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guiones")
        if not os.path.exists(base_dir): os.makedirs(base_dir, exist_ok=True)
        
        dlg = wx.FileDialog(self, "Cargar Guion de Canción", defaultDir=base_dir, wildcard="Archivos de Guion (*.txt)|*.txt", style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                self.scroller.script_blocks.clear()
                for line in lines:
                    line_s = line.strip()
                    if not line_s or line_s.startswith('#'): continue
                    
                    if line_s.lower().startswith('bpm:'):
                        self.scroller.script_bpm = int(line_s.split(':')[1].strip())
                        self.spin_script_bpm.SetValue(self.scroller.script_bpm)
                    elif line_s.lower().startswith('tiempos_compas:'):
                        self.scroller.script_beats_per_line = int(line_s.split(':')[1].strip())
                        self.spin_script_tiempos.SetValue(self.scroller.script_beats_per_line)
                        self.update_script_disparo_choices()
                    elif line_s.lower().startswith('reposo:'):
                        self.scroller.script_lead_in_bars = int(line_s.split(':')[1].strip())
                        self.spin_script_reposo.SetValue(self.scroller.script_lead_in_bars)
                    elif line_s.lower().startswith('disparos:'):
                        disp_raw = line_s.split(':')[1].strip()
                        beats = set([int(x)-1 for x in disp_raw.split(',') if x.strip().isdigit()])
                        if beats:
                            self.scroller.script_advance_beats = beats
                            self.update_script_disparo_choices()
                    elif ':' in line_s:
                        t, c = line_s.split(':')
                        t_clean = t.strip().lower()
                        c_clean = int(c.strip())
                        tipo = 'bajar' if t_clean in ('bajar', 'letra') else 'silencio'
                        self.scroller.script_blocks.append((tipo, c_clean))
                        
                self.update_blocks_list_ui()
                self.chk_usar_guion.SetValue(True)
                self.scroller.mode = "guion"
                wx.MessageBox(f"Guion '{os.path.basename(path)}' cargado exitosamente.", "Éxito", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Error cargando el guion: {e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def on_guardar_guion_txt(self, event=None):
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "guiones")
        if not os.path.exists(base_dir): os.makedirs(base_dir, exist_ok=True)
        
        dlg = wx.FileDialog(self, "Guardar Guion de Canción", defaultDir=base_dir, defaultFile="Mi_Cancion.txt", wildcard="Archivos de Guion (*.txt)|*.txt", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(f"# Guion de Canción - {APP_NAME} v{APP_VERSION}\n")
                    f.write(f"BPM: {self.scroller.script_bpm}\n")
                    f.write(f"TIEMPOS_COMPAS: {self.scroller.script_beats_per_line}\n")
                    f.write(f"REPOSO: {self.scroller.script_lead_in_bars}\n")
                    disp_str = ",".join([str(x+1) for x in sorted(list(self.scroller.script_advance_beats))])
                    f.write(f"DISPAROS: {disp_str}\n\n")
                    
                    for tipo, compases in self.scroller.script_blocks:
                        f.write(f"{tipo}: {compases}\n")
                        
                wx.MessageBox(f"Guardado exitosamente en '{os.path.basename(path)}'.", "Éxito", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"Error guardando el guion: {e}", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def update_status_log(self, text):
        def _update():
            self.txt_log.AppendText(text + "\n")
        wx.CallAfter(_update)

    def update_blocks_list_ui(self):
        self.lst_bloques.Clear()
        for idx, (tipo, compases) in enumerate(self.scroller.script_blocks):
            nombre_tipo = "Bajar Letra" if tipo == 'bajar' else "Silencio / Instrumental"
            self.lst_bloques.Append(f"Bloque {idx+1}: {nombre_tipo} — {compases} compases")
        self.save_config()

    def on_agregar_bloque(self, event=None):
        sel = self.combo_tipo_bloque.GetSelection()
        tipo = 'bajar' if sel == 0 else 'silencio'
        compases = self.spin_compases.GetValue()
        
        self.scroller.script_blocks.append((tipo, compases))
        self.update_blocks_list_ui()
        self.lst_bloques.SetSelection(len(self.scroller.script_blocks) - 1)

    def on_eliminar_bloque(self, event=None):
        sel = self.lst_bloques.GetSelection()
        if sel != wx.NOT_FOUND and 0 <= sel < len(self.scroller.script_blocks):
            del self.scroller.script_blocks[sel]
            self.update_blocks_list_ui()
            if self.scroller.script_blocks:
                new_sel = min(sel, len(self.scroller.script_blocks) - 1)
                self.lst_bloques.SetSelection(new_sel)

    def on_subir_bloque(self, event=None):
        sel = self.lst_bloques.GetSelection()
        if sel > 0 and sel < len(self.scroller.script_blocks):
            self.scroller.script_blocks[sel], self.scroller.script_blocks[sel-1] = (
                self.scroller.script_blocks[sel-1], self.scroller.script_blocks[sel]
            )
            self.update_blocks_list_ui()
            self.lst_bloques.SetSelection(sel - 1)

    def on_bajar_bloque(self, event=None):
        sel = self.lst_bloques.GetSelection()
        if sel != wx.NOT_FOUND and sel < len(self.scroller.script_blocks) - 1:
            self.scroller.script_blocks[sel], self.scroller.script_blocks[sel+1] = (
                self.scroller.script_blocks[sel+1], self.scroller.script_blocks[sel]
            )
            self.update_blocks_list_ui()
            self.lst_bloques.SetSelection(sel + 1)

    def on_vaciar_guion(self, event=None):
        if self.scroller.script_blocks:
            self.scroller.script_blocks.clear()
            self.update_blocks_list_ui()

    def on_list_key_down(self, event):
        keycode = event.GetKeyCode()
        if keycode in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self.on_eliminar_bloque()
        else:
            event.Skip()

    def on_guion_mode_toggle(self, event):
        if self.chk_usar_guion.IsChecked():
            self.scroller.mode = "guion"
            self.update_status_log("[MODO] Cambiado a Modo Guion Avanzado.")
        else:
            self.scroller.mode = "simple"
            self.update_status_log("[MODO] Cambiado a Modo Simple.")

    def parse_hotkey_str(self, hotkey_str):
        partes = hotkey_str.lower().split('+')
        mods = wx.MOD_NONE
        main_key = partes[-1]
        
        for p in partes[:-1]:
            if p in ('ctrl', 'control'): mods |= wx.MOD_CONTROL
            elif p == 'alt': mods |= wx.MOD_ALT
            elif p == 'shift': mods |= wx.MOD_SHIFT
            elif p in ('win', 'windows'): mods |= wx.MOD_WIN
            
        vks = []
        if main_key in NUMPAD_DUAL_MAP:
            vks = NUMPAD_DUAL_MAP[main_key]
        elif len(main_key) == 1:
            res = ctypes.windll.user32.VkKeyScanW(ord(main_key))
            vks = [(res & 0xFF)] if res != -1 else [0x6B]
        else:
            vks = [0x6B]
            
        return mods, vks

    def setup_global_hotkeys(self):
        for hid in self.registered_ids:
            try: self.UnregisterHotKey(hid)
            except: pass
        self.registered_ids.clear()

        mod_toggle, vks_toggle = self.parse_hotkey_str(self.tecla_toggle)
        mod_stop, vks_stop = self.parse_hotkey_str(self.tecla_stop)
        mod_call_tap, vks_call_tap = self.parse_hotkey_str(self.tecla_call_tap)

        for idx, vk in enumerate(vks_toggle):
            hid = HOTKEY_ID_BASE_TOGGLE + idx
            self.RegisterHotKey(hid, mod_toggle, vk)
            self.registered_ids.append(hid)

        for idx, vk in enumerate(vks_stop):
            hid = HOTKEY_ID_BASE_STOP + idx
            self.RegisterHotKey(hid, mod_stop, vk)
            self.registered_ids.append(hid)

        for idx, vk in enumerate(vks_call_tap):
            hid = HOTKEY_ID_BASE_TAP_TRIGGER + idx
            self.RegisterHotKey(hid, mod_call_tap, vk)
            self.registered_ids.append(hid)
        
        self.Bind(wx.EVT_HOTKEY, self.on_global_hotkey)

    def on_global_hotkey(self, event):
        eventId = event.GetId()
        if eventId >= HOTKEY_ID_BASE_TOGGLE and eventId < HOTKEY_ID_BASE_STOP:
            if self.is_tap_session_active:
                self.on_tap_trigger()
            else:
                self.scroller.start_or_pause()
        elif eventId >= HOTKEY_ID_BASE_STOP and eventId < HOTKEY_ID_BASE_TAP_TRIGGER:
            self.scroller.stop()
        elif eventId >= HOTKEY_ID_BASE_TAP_TRIGGER:
            self.on_tap_trigger()

    def start_capture(self, target, button_ctrl):
        self.capturing_target = target
        self.active_button = button_ctrl
        self.active_button.Disable()
        self.active_button.SetLabel("PRESIONA LA TECLA AHORA...")

    def on_key_hook(self, event):
        if self.capturing_target:
            key_name = self.wx_key_to_name(event)
            if key_name:
                target = self.capturing_target
                self.capturing_target = None
                self.active_button.Enable()
                
                if target == 'toggle':
                    self.tecla_toggle = key_name
                    self.lbl_tecla_toggle.SetLabel(f"Iniciar/Pausar: [{key_name}]")
                    self.btn_iniciar_simple.SetLabel(f"INICIAR / PAUSAR (O presiona {key_name})")
                    self.btn_cap_toggle.SetLabel("Capturar Iniciar/Pausar")
                    self.setup_global_hotkeys()
                elif target == 'stop':
                    self.tecla_stop = key_name
                    self.lbl_tecla_stop.SetLabel(f"Reiniciar: [{key_name}]")
                    self.btn_cap_stop.SetLabel("Capturar Reiniciar")
                    self.setup_global_hotkeys()
                elif target == 'avance':
                    self.tecla_avance = key_name
                    self.scroller.tecla_avance = key_name
                    self.lbl_tecla_avance.SetLabel(f"Tecla de Avance: [{key_name}]")
                    self.btn_cap_avance.SetLabel("Capturar Tecla de Avance")
                elif target == 'call_tap':
                    self.tecla_call_tap = key_name
                    self.lbl_tecla_call_tap.SetLabel(f"Activar Calibrador Tap: [{key_name}]")
                    self.btn_tap.SetLabel(f"Calibrar Ritmo (O presiona {key_name})")
                    self.btn_cap_call_tap.SetLabel("Capturar Activar Tap")
                    self.setup_global_hotkeys()
                    
                self.save_config()
                wx.MessageBox(f"Guardado exitosamente: {key_name}", "Capturadora Nativa")
                return

        keycode = event.GetUnicodeKey()
        if keycode in (ord('R'), ord('r')):
            obj = event.GetEventObject()
            if not isinstance(obj, wx.TextCtrl):
                self.on_reset_hotkeys()
                return
        event.Skip()

    def wx_key_to_name(self, event):
        key = event.GetKeyCode()
        mods = []
        if event.ControlDown(): mods.append('ctrl')
        if event.AltDown(): mods.append('alt')
        if event.ShiftDown(): mods.append('shift')
        
        if key in (wx.WXK_CONTROL, wx.WXK_ALT, wx.WXK_SHIFT):
            return None
            
        special_names = {
            wx.WXK_DOWN: 'down',
            wx.WXK_UP: 'up',
            wx.WXK_LEFT: 'left',
            wx.WXK_RIGHT: 'right',
            wx.WXK_PAGEDOWN: 'page down',
            wx.WXK_PAGEUP: 'page up',
            wx.WXK_SPACE: 'space',
            wx.WXK_RETURN: 'enter',
            wx.WXK_TAB: 'tab',
            wx.WXK_NUMPAD_ADD: '+',
            wx.WXK_NUMPAD_SUBTRACT: '-',
            wx.WXK_NUMPAD8: '8',
            wx.WXK_NUMPAD2: '2',
            wx.WXK_NUMPAD0: '0',
            wx.WXK_NUMPAD1: '1',
            wx.WXK_NUMPAD3: '3',
            wx.WXK_NUMPAD4: '4',
            wx.WXK_NUMPAD5: '5',
            wx.WXK_NUMPAD6: '6',
            wx.WXK_NUMPAD7: '7',
            wx.WXK_NUMPAD9: '9',
            wx.WXK_ADD: '+',
            wx.WXK_SUBTRACT: '-',
            wx.WXK_F12: 'f12',
            wx.WXK_F11: 'f11',
            wx.WXK_F10: 'f10',
            wx.WXK_PAUSE: 'pause',
        }
        
        main_key = special_names.get(key)
        if not main_key:
            unicode_char = event.GetUnicodeKey()
            if unicode_char and unicode_char != wx.WXK_NONE:
                main_key = chr(unicode_char).lower()
            else:
                main_key = str(key)
                
        if mods:
            return "+".join(mods) + "+" + main_key
        else:
            return main_key

    def on_reset_hotkeys(self, event=None):
        self.tecla_toggle = "+"
        self.tecla_stop = "-"
        self.tecla_avance = "down"
        self.tecla_call_tap = "ctrl+alt+t"
        self.lbl_tecla_toggle.SetLabel(f"Iniciar/Pausar: [{self.tecla_toggle}]")
        self.lbl_tecla_stop.SetLabel(f"Reiniciar: [{self.tecla_stop}]")
        self.lbl_tecla_avance.SetLabel(f"Tecla de Avance: [{self.tecla_avance}]")
        self.lbl_tecla_call_tap.SetLabel(f"Activar Calibrador Tap: [{self.tecla_call_tap}]")
        self.btn_iniciar_simple.SetLabel(f"INICIAR / PAUSAR (O presiona {self.tecla_toggle})")
        self.btn_tap.SetLabel(f"Calibrar Ritmo (O presiona {self.tecla_call_tap})")
        
        self.scroller.tecla_avance = self.tecla_avance
        self.save_config()
        self.setup_global_hotkeys()
        wx.MessageBox("Atajos restaurados a los valores por defecto (+, -, ctrl+alt+t).", "Restaurado", wx.OK | wx.ICON_INFORMATION)

    def load_config(self):
        self.config = configparser.ConfigParser()
        self.tecla_toggle = "+"
        self.tecla_stop = "-"
        self.tecla_avance = "down"
        self.tecla_call_tap = "ctrl+alt+t"
        
        if os.path.exists(config_file):
            self.config.read(config_file, encoding='utf-8')
            try:
                self.tecla_toggle = self.config['Atajos_Secuenciador'].get('iniciar_pausar', '+')
                self.tecla_stop = self.config['Atajos_Secuenciador'].get('reiniciar', '-')
                self.tecla_avance = self.config['Atajos_Secuenciador'].get('tecla_avance', 'down')
                self.tecla_call_tap = self.config['Atajos_Secuenciador'].get('activar_tap', 'ctrl+alt+t')
                
                # Cargar Modo Simple
                self.scroller.simple_bpm = int(self.config['Atajos_Secuenciador'].get('simple_bpm', '120'))
                self.scroller.simple_beats_per_line = int(self.config['Atajos_Secuenciador'].get('simple_beats_per_line', '4'))
                self.scroller.simple_lead_in_bars = int(self.config['Atajos_Secuenciador'].get('simple_lead_in_bars', '1'))
                s_beats = self.config['Atajos_Secuenciador'].get('simple_advance_beats', '0')
                self.scroller.simple_advance_beats = set([int(x) for x in s_beats.split(',') if x.isdigit()])
                
                # Cargar Modo Guion
                if self.config.has_section('Modo_Guion'):
                    self.scroller.script_bpm = int(self.config['Modo_Guion'].get('bpm', '120'))
                    self.scroller.script_beats_per_line = int(self.config['Modo_Guion'].get('beats_per_line', '4'))
                    self.scroller.script_lead_in_bars = int(self.config['Modo_Guion'].get('lead_in_bars', '1'))
                    g_beats = self.config['Modo_Guion'].get('advance_beats', '0')
                    self.scroller.script_advance_beats = set([int(x) for x in g_beats.split(',') if x.isdigit()])
                
                if self.config.has_section('Guion_Bloques'):
                    self.scroller.script_blocks.clear()
                    blocks_raw = self.config['Guion_Bloques'].get('lista', '')
                    if blocks_raw:
                        for b in blocks_raw.split('|'):
                            if ':' in b:
                                t, c = b.split(':')
                                self.scroller.script_blocks.append((t, int(c)))
            except KeyError:
                pass
        else:
            self.save_config()
            
        self.scroller.tecla_avance = self.tecla_avance
        wx.CallAfter(self.update_blocks_list_ui)
        wx.CallAfter(self.update_simple_disparo_choices)
        wx.CallAfter(self.update_script_disparo_choices)

    def save_config(self):
        if not self.config.has_section('Compasero'):
            self.config.add_section('Compasero')
        self.config['Compasero']['version'] = APP_VERSION
        
        if not self.config.has_section('Atajos_Secuenciador'):
            self.config.add_section('Atajos_Secuenciador')
        self.config['Atajos_Secuenciador']['iniciar_pausar'] = self.tecla_toggle
        self.config['Atajos_Secuenciador']['reiniciar'] = self.tecla_stop
        self.config['Atajos_Secuenciador']['tecla_avance'] = self.tecla_avance
        self.config['Atajos_Secuenciador']['activar_tap'] = self.tecla_call_tap
        self.config['Atajos_Secuenciador']['simple_bpm'] = str(self.scroller.simple_bpm)
        self.config['Atajos_Secuenciador']['simple_beats_per_line'] = str(self.scroller.simple_beats_per_line)
        self.config['Atajos_Secuenciador']['simple_lead_in_bars'] = str(self.scroller.simple_lead_in_bars)
        self.config['Atajos_Secuenciador']['simple_advance_beats'] = ",".join([str(x) for x in sorted(list(self.scroller.simple_advance_beats))])
        
        if not self.config.has_section('Modo_Guion'):
            self.config.add_section('Modo_Guion')
        self.config['Modo_Guion']['bpm'] = str(self.scroller.script_bpm)
        self.config['Modo_Guion']['beats_per_line'] = str(self.scroller.script_beats_per_line)
        self.config['Modo_Guion']['lead_in_bars'] = str(self.scroller.script_lead_in_bars)
        self.config['Modo_Guion']['advance_beats'] = ",".join([str(x) for x in sorted(list(self.scroller.script_advance_beats))])
        
        if not self.config.has_section('Guion_Bloques'):
            self.config.add_section('Guion_Bloques')
        
        blocks_str = "|".join([f"{t}:{c}" for t, c in self.scroller.script_blocks])
        self.config['Guion_Bloques']['lista'] = blocks_str
        
        with open(config_file, 'w', encoding='utf-8') as configfile:
            self.config.write(configfile)
