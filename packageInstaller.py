#!/usr/bin/env python3
import sys
import subprocess
import os
import time
import curses
import signal

class PackageManager:
    def __init__(self):
        self.pm = self._detect_pm()
        self._cache = {}
    
    def _detect_pm(self):
        for pm, path in [('apt', '/usr/bin/apt'), ('dnf', '/usr/bin/dnf'), ('pacman', '/usr/bin/pacman')]:
            if os.path.exists(path):
                return pm
        return None
    
    def update_cache(self):
        if self.pm == 'apt':
            subprocess.run(['sudo', 'apt', 'update'], capture_output=True, timeout=60)
        elif self.pm == 'dnf':
            subprocess.run(['sudo', 'dnf', 'check-update'], capture_output=True, timeout=60)
        elif self.pm == 'pacman':
            subprocess.run(['sudo', 'pacman', '-Sy'], capture_output=True, timeout=60)
    
    def search(self, query):
        if self.pm == 'apt':
            result = subprocess.run(['apt-cache', 'search', query], capture_output=True, text=True, timeout=30)
            pkgs = []
            for line in result.stdout.strip().split('\n'):
                if ' - ' in line:
                    parts = line.split(' - ', 1)
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ''
                    pkgs.append((self._normalize_name(name), desc, name))
            return pkgs
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'search', query], capture_output=True, text=True, timeout=30)
            pkgs = []
            for line in result.stdout.split('\n'):
                if '.x86_64' in line or '.noarch' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        name = parts[0].strip().split()[0]
                        pkgs.append((self._normalize_name(name), parts[1].strip(), name))
            return pkgs
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Ss', query], capture_output=True, text=True, timeout=30)
            pkgs = []
            for line in result.stdout.split('\n'):
                if line.startswith('[') or not line.strip() or '/' not in line:
                    continue
                parts = line.split('/', 1)
                if len(parts) == 2:
                    name_desc = parts[1].split(' ', 1)
                    name = self._normalize_name(name_desc[0])
                    desc = name_desc[1] if len(name_desc) > 1 else ''
                    pkgs.append((name, desc, name_desc[0]))
            return pkgs
        return []
    
    def _normalize_name(self, name):
        suffixes = ['-dev', '-doc', '-dbg', '-common', '-utils', '-tools', '-bin', '-x86', '-x64', '-amd64', '-i386', '-arm64', '-armhf', '-64bit', '-32bit']
        for s in suffixes:
            if name.endswith(s):
                return name[:-len(s)]
        return name
    
    def get_info(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['apt-cache', 'show', package], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if line.startswith('Description:'):
                    return line.replace('Description:', '').strip()
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'info', package], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'Description :' in line:
                    return line.split(':', 1)[1].strip()
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Si', package], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'Description' in line:
                    return line.split(':', 1)[1].strip()
        return ''
    
    def is_installed(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
            return 'ii' in result.stdout
        return False
    
    def install(self, package):
        if self.pm == 'apt':
            cmd = ['sudo', 'apt', 'install', '-y', package]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stdout[-2000:]
    
    def get_pm_name(self):
        names = {'apt': 'APT', 'dnf': 'DNF', 'pacman': 'Pacman'}
        return names.get(self.pm, 'Unknown')


TAGS = {
    'qemu': ['qemu', 'kvm', 'virtual', 'emulator', 'virtualization', 'vm'],
    'dosbox': ['dosbox', 'dos', 'msdos'],
    'chromium': ['chromium', 'chrome', 'browser', 'web'],
    'mame': ['mame', 'arcade', 'emulator'],
    'vice': ['vice', 'c64', 'commodore', 'emulator'],
    'fceux': ['fceux', 'nes', 'nintendo', 'emulator'],
    'wine': ['wine', 'windows', 'win32'],
    'code': ['code', 'vscode', 'visual studio', 'ide', 'editor'],
    'steam': ['steam', 'gaming', 'games'],
    'vlc': ['vlc', 'video', 'media', 'player'],
    'blender': ['blender', '3d', 'modeling'],
    'gimp': ['gimp', 'image', 'photo', 'graphics'],
    '64tass': ['64tass', '6502', 'assembler'],
    'cc65': ['cc65', '6502', 'c compiler'],
    'virtualbox': ['virtualbox', 'virtual', 'vm'],
}

KNOWN_APPS = {
    'qemu-system-x86': 'QEMU (x86)',
    'qemu': 'QEMU',
    'dosbox': 'DOSBox',
    'chromium': 'Chromium',
    'chromium-driver': 'Chromium Driver',
    'code': 'VS Code',
    'mame': 'MAME',
    'vice': 'VICE (C64)',
    'fceux': 'FCEUX (NES)',
    'steam': 'Steam',
    'vlc': 'VLC',
    'blender': 'Blender',
    'gimp': 'GIMP',
    'libreoffice': 'LibreOffice',
    'wine': 'Wine',
    'godot': 'Godot',
    'discord': 'Discord',
    'obs': 'OBS Studio',
    'audacity': 'Audacity',
    'inkscape': 'Inkscape',
    'gparted': 'GParted',
    'htop': 'htop',
    'docker': 'Docker',
}


class PackageInstallerUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.pm = PackageManager()
        self.results = []
        self.search_query = ''
        self.current_idx = 0
        self.start_idx = 0
        self.category_idx = 0
        self.categories = ['All', 'Tools', 'Apps']
        self.mode = 'search'
        self.selected_pkg = None
        self.message = ''
        self.message_time = 0
        self.search_time = 0
        self.needs_redraw = True
        curses.curs_set(0)
    
    def resize(self):
        self.height, self.width = self.stdscr.getmaxyx()
    
    def draw(self):
        if not self.needs_redraw:
            return
        self.resize()
        self.stdscr.clear()
        
        try:
            self._draw_header()
            self._draw_category_bar()
            self._draw_search_bar()
            
            if self.mode == 'search':
                self._draw_package_list()
            elif self.mode == 'details':
                self._draw_details()
            
            self._draw_status_bar()
        except curses.error:
            pass
        
        self.stdscr.refresh()
        self.needs_redraw = False
    
    def _draw_header(self):
        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(0, 0, '╔' + '═' * (self.width - 2) + '╗')
        title = f' Package Installer [{self.pm.get_pm_name()}] '
        self.stdscr.addstr(1, max(1, (self.width - len(title)) // 2), title)
        self.stdscr.addstr(2, 0, '╚' + '═' * (self.width - 2) + '╝')
        self.stdscr.attroff(curses.color_pair(1))
    
    def _draw_category_bar(self):
        x = 2
        for i, cat in enumerate(self.categories):
            try:
                if i == self.category_idx:
                    self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(4, x, f'[{cat}]')
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(4, x, f' {cat} ')
                x += len(cat) + 3
            except curses.error:
                pass
    
    def _draw_search_bar(self):
        try:
            self.stdscr.addstr(5, 2, 'Search: ')
            query_display = self.search_query + ' '
            self.stdscr.addstr(5, 10, query_display[:self.width - 15])
        except curses.error:
            pass
    
    def _draw_package_list(self):
        if not self.results:
            try:
                self.stdscr.addstr(7, 2, 'Type to search...')
                self.stdscr.addstr(8, 2, 'Examples: qemu, chromium, code, dosbox')
                return
            except curses.error:
                pass
            return
        
        try:
            list_y = 7
            max_items = min(self.height - list_y - 3, 20)
            
            for i in range(max_items):
                idx = self.start_idx + i
                if idx >= len(self.results):
                    break
                
                display_name, desc, real_name = self.results[idx]
                installed = self.pm.is_installed(real_name)
                y = list_y + i
                
                if idx == self.current_idx:
                    self.stdscr.attron(curses.color_pair(2))
                    marker = '>'
                else:
                    marker = ' '
                
                self.stdscr.addstr(y, 2, marker)
                
                if installed:
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(y, 4, '✓')
                    self.stdscr.attroff(curses.color_pair(3))
                else:
                    self.stdscr.addstr(y, 4, ' ')
                
                name_len = min(len(display_name), 25)
                self.stdscr.addstr(y, 7, display_name[:name_len])
                
                if idx == self.current_idx and desc:
                    desc_len = min(len(desc), self.width - 10)
                    self.stdscr.addstr(y + 1, 9, desc[:desc_len])
        except curses.error:
            pass
    
    def _draw_details(self):
        if not self.selected_pkg:
            return
        
        display_name, desc, real_name = self.selected_pkg
        installed = self.pm.is_installed(real_name)
        info = self.pm.get_info(real_name) or desc
        
        try:
            self.stdscr.addstr(7, 2, f'Package: {display_name}')
            status = 'INSTALLED' if installed else 'NOT INSTALLED'
            color = 3 if installed else 1
            self.stdscr.attron(curses.color_pair(color))
            self.stdscr.addstr(8, 2, f'Status: {status}')
            self.stdscr.attroff(curses.color_pair(color))
            
            if real_name != display_name:
                self.stdscr.addstr(9, 2, f'Real name: {real_name}')
            
            self.stdscr.addstr(10, 2, 'Description:')
            y = 11
            words = info.split()
            line = ''
            for word in words:
                if len(line) + len(word) < self.width - 8:
                    line += word + ' '
                else:
                    if y < self.height - 4:
                        self.stdscr.addstr(y, 4, line)
                        y += 1
                    line = word + ' '
            if line and y < self.height - 4:
                self.stdscr.addstr(y, 4, line)
            
            action = '[ Uninstall ]' if installed else '[ Install ]'
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(self.height - 4, 2, action)
            self.stdscr.attroff(curses.color_pair(2))
            self.stdscr.addstr(self.height - 4, 18, '< Enter >')
        except curses.error:
            pass
    
    def _draw_status_bar(self):
        try:
            if self.message and time.time() - self.message_time < 3:
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(self.height - 2, 2, self.message[:self.width - 4])
                self.stdscr.attroff(curses.color_pair(3))
            
            count = len(self.results)
            status = f' {count} packages | ←→ Category | ↑↓ Navigate | Enter: Select | Tab: Back | Ctrl+C: Quit '
            self.stdscr.addstr(self.height - 1, 0, status[:self.width])
        except curses.error:
            pass
    
    def show_message(self, msg):
        self.message = msg
        self.message_time = time.time()
        self.needs_redraw = True
    
    def handle_input(self, key):
        if key == -1:
            return
        
        if self.mode == 'search':
            self._handle_search_input(key)
        elif self.mode == 'details':
            self._handle_details_input(key)
        
        self.needs_redraw = True
    
    def _handle_search_input(self, key):
        if key == curses.KEY_UP:
            if self.current_idx > 0:
                self.current_idx -= 1
                if self.current_idx < self.start_idx:
                    self.start_idx = max(0, self.start_idx - 5)
        elif key == curses.KEY_DOWN:
            if self.current_idx < len(self.results) - 1:
                self.current_idx += 1
                if self.current_idx >= self.start_idx + 15:
                    self.start_idx += 5
        elif key == curses.KEY_LEFT:
            if self.category_idx > 0:
                self.category_idx -= 1
                self._do_search()
        elif key == curses.KEY_RIGHT:
            if self.category_idx < len(self.categories) - 1:
                self.category_idx += 1
                self._do_search()
        elif key == curses.KEY_ENTER or key == 10:
            if self.results:
                self.selected_pkg = self.results[self.current_idx]
                self.mode = 'details'
        elif key == 9:
            pass
        elif key == curses.KEY_BACKSPACE or key == 127:
            self.search_query = self.search_query[:-1]
            self._do_search()
        elif key >= 32 and key <= 126:
            self.search_query += chr(key)
            self._do_search()
        elif key == 27:
            self.search_query = ''
            self.results = []
    
    def _handle_details_input(self, key):
        if key == curses.KEY_ENTER or key == 10:
            if self.selected_pkg:
                _, _, real_name = self.selected_pkg
                if self.pm.is_installed(real_name):
                    self.show_message('Use apt remove to uninstall')
                else:
                    success, output = self.pm.install(real_name)
                    if success:
                        self.show_message(f'{self.selected_pkg[0]} installed!')
                    else:
                        self.show_message('Installation failed')
                self.mode = 'search'
        elif key in [9, 27, curses.KEY_LEFT]:
            self.mode = 'search'
    
    def _do_search(self):
        if not self.search_query:
            self.results = []
            return
        
        all_results = self.pm.search(self.search_query)
        
        tagged_results = []
        search_lower = self.search_query.lower()
        
        for display_name, desc, real_name in all_results:
            matched_tag = None
            for tag_name, tag_terms in TAGS.items():
                if search_lower in tag_terms or any(t in search_lower for t in tag_terms):
                    matched_tag = tag_name
                    break
            
            score = 0
            if matched_tag:
                score += 100
            
            name_lower = display_name.lower()
            if search_lower in name_lower:
                score += 50
            if search_lower in desc.lower():
                score += 10
            
            for tag_name, tag_terms in TAGS.items():
                if any(t in name_lower for t in tag_terms):
                    score += 20
                    display_name = KNOWN_APPS.get(tag_name, display_name)
            
            if score > 0:
                tagged_results.append((display_name, desc, real_name, score))
        
        tagged_results.sort(key=lambda x: -x[3])
        self.results = [(d, n, r) for d, n, r, s in tagged_results]
        self.current_idx = 0
        self.start_idx = 0


def main(stdscr):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    curses.init_pair(2, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    
    stdscr.keypad(True)
    stdscr.nodelay(True)
    stdscr.timeout(100)
    stdscr.clear()
    
    pm = PackageManager()
    if pm.pm is None:
        stdscr.addstr(0, 0, 'No supported package manager found!')
        stdscr.refresh()
        stdscr.getch()
        return
    
    try:
        pm.update_cache()
    except:
        pass
    
    ui = PackageInstallerUI(stdscr)
    ui.needs_redraw = True
    
    while True:
        ui.draw()
        key = ui.stdscr.getch()
        if key == 3:
            break
        ui.handle_input(key)


if __name__ == '__main__':
    curses.wrapper(main)