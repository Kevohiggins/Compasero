import threading
import time
from audio import play_click
from input_win32 import win32_send_key

class AutoScroller:
    def __init__(self, log_callback=None):
        self.is_running = False
        self.mode = "simple"
        
        # Parámetros para Modo Simple
        self.simple_bpm = 120
        self.simple_beats_per_line = 4
        self.simple_advance_beats = {0}
        self.simple_lead_in_bars = 1
        
        # Parámetros independientes para Modo Guion Avanzado
        self.script_bpm = 120
        self.script_beats_per_line = 4
        self.script_advance_beats = {0}
        self.script_lead_in_bars = 1
        self.script_blocks = []
        
        self.enable_metronome_sound = True
        self.current_block_idx = 0
        self.thread = None
        self.stop_requested = False
        self.wake_event = threading.Event()
        self.tecla_avance = "down"
        self.log_callback = log_callback
        self.pending_lead_in_bars = 0

    @property
    def bpm(self):
        return self.script_bpm if self.mode == "guion" else self.simple_bpm

    @property
    def beats_per_line(self):
        return self.script_beats_per_line if self.mode == "guion" else self.simple_beats_per_line

    @property
    def advance_beats(self):
        return self.script_advance_beats if self.mode == "guion" else self.simple_advance_beats

    @property
    def lead_in_bars(self):
        return self.script_lead_in_bars if self.mode == "guion" else self.simple_lead_in_bars

    @property
    def simple_interval(self):
        if self.bpm <= 0: return 3.0
        sec_per_beat = 60.0 / self.bpm
        return sec_per_beat * self.beats_per_line

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        print(msg)

    def start_or_pause(self):
        if self.is_running:
            self.is_running = False
            self.log("\n[PAUSADO] Avance detenido en el punto actual.")
        else:
            self.is_running = True
            self.stop_requested = False
            self.pending_lead_in_bars = self.lead_in_bars  # Activar reposo CADA VEZ que se inicia o reanuda
            self.wake_event.set()
            
            active_bpm = self.bpm
            active_beats_bar = self.beats_per_line
            active_triggers = self.advance_beats
            
            tiempos_str = ", ".join([f"Tiempo {i+1}" for i in sorted(list(active_triggers))])
            if self.mode == "simple":
                self.log(f"\n[INICIADO/REANUDADO] Modo Simple ({active_bpm} BPM, compás de {active_beats_bar} tiempos, reposo: {self.lead_in_bars} compás(es), avanza en: {tiempos_str})...")
            else:
                self.log(f"\n[INICIADO/REANUDADO] Modo Guion Avanzado ({active_bpm} BPM, compás de {active_beats_bar} tiempos, reposo: {self.lead_in_bars} compás(es)): Ejecutando Bloque {self.current_block_idx + 1} de {len(self.script_blocks)}...")

            if not self.thread or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._run_loop, daemon=True)
                self.thread.start()

    def stop(self):
        self.is_running = False
        self.stop_requested = True
        self.wake_event.set()
        self.current_block_idx = 0
        self.pending_lead_in_bars = 0
        self.log("\n[DETENIDO] Reiniciado al Bloque 1, Compás 1.")

    def _run_loop(self):
        while not self.stop_requested:
            if not self.is_running:
                self.wake_event.wait(timeout=0.05)
                self.wake_event.clear()
                continue

            active_bpm = self.bpm
            active_beats_bar = self.beats_per_line
            active_triggers = self.advance_beats

            num_beats = max(1, active_beats_bar)
            sec_per_beat = 60.0 / max(1, active_bpm)

            # COMPASES DE CUENTA / REPOSO CONFIGURABLES (Se ejecutan cada vez al Iniciar o Reanudar)
            while self.pending_lead_in_bars > 0:
                if self.stop_requested or not self.is_running: break
                total_reposo = self.lead_in_bars
                actual_num = total_reposo - self.pending_lead_in_bars + 1
                self.log(f"--> Compás de reposo/cuenta ({actual_num} de {total_reposo})...")
                
                for b in range(num_beats):
                    if self.stop_requested or not self.is_running: break
                    play_click(is_accent=(b == 0), enable_sound=self.enable_metronome_sound)
                    
                    start_time = time.time()
                    while (time.time() - start_time) < sec_per_beat:
                        if self.stop_requested or not self.is_running: break
                        time.sleep(0.005)
                
                if not self.stop_requested and self.is_running:
                    self.pending_lead_in_bars -= 1

            if self.stop_requested or not self.is_running:
                continue

            if self.mode == "simple":
                for b in range(num_beats):
                    if self.stop_requested or not self.is_running: break
                    
                    play_click(is_accent=(b == 0), enable_sound=self.enable_metronome_sound)
                    
                    if b in active_triggers and not self.stop_requested and self.is_running:
                        win32_send_key(self.tecla_avance)
                    
                    start_time = time.time()
                    while (time.time() - start_time) < sec_per_beat:
                        if self.stop_requested or not self.is_running: break
                        time.sleep(0.005)

            elif self.mode == "guion":
                if not self.script_blocks or self.current_block_idx >= len(self.script_blocks):
                    self.is_running = False
                    self.log("\n[FIN] Guion por compases completado.")
                    self.current_block_idx = 0
                    self.pending_lead_in_bars = 0
                    break

                tipo, cantidad_compases = self.script_blocks[self.current_block_idx]
                nombre_tipo = "Bajar Letra" if tipo == 'bajar' else "Silencio / Instrumental"
                self.log(f"--> Reproduciendo Bloque {self.current_block_idx + 1}/{len(self.script_blocks)}: {nombre_tipo} ({cantidad_compases} compases)")

                compases_hechos = 0
                while compases_hechos < cantidad_compases and not self.stop_requested and self.is_running:
                    for b in range(num_beats):
                        if self.stop_requested or not self.is_running: break
                        
                        play_click(is_accent=(b == 0), enable_sound=self.enable_metronome_sound)
                        
                        if tipo == 'bajar' and b in active_triggers and not self.stop_requested and self.is_running:
                            win32_send_key(self.tecla_avance)

                        start_time = time.time()
                        while (time.time() - start_time) < sec_per_beat:
                            if self.stop_requested or not self.is_running: break
                            time.sleep(0.005)

                    compases_hechos += 1

                if not self.stop_requested and self.is_running:
                    self.current_block_idx += 1
