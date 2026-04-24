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
    
    def _detect_pm(self):
        if os.path.exists('/usr/bin/apt'):
            return 'apt'
        elif os.path.exists('/usr/bin/dnf'):
            return 'dnf'
        elif os.path.exists('/usr/bin/pacman'):
            return 'pacman'
        elif os.path.exists('/usr/bin/zypper'):
            return 'zypper'
        elif os.path.exists('/usr/bin/xbps-query'):
            return 'xbps'
        elif os.path.exists('/usr/bin/apk'):
            return 'apk'
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
                    pkgs.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ''))
            return pkgs
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'search', query], capture_output=True, text=True, timeout=30)
            pkgs = []
            for line in result.stdout.split('\n'):
                if line.startswith('Last metadata') or not line.strip():
                    continue
                if '.x86_64' in line or '.noarch' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        name_parts = parts[0].strip().split()
                        if name_parts:
                            pkgs.append((name_parts[0], parts[1].strip() if len(parts) > 1 else ''))
            return pkgs
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Ss', query], capture_output=True, text=True, timeout=30)
            pkgs = []
            for line in result.stdout.split('\n'):
                if line.startswith('[') or not line.strip():
                    continue
                if ' :: ' in line:
                    line = line.split(' :: ', 1)[1]
                if '/' in line:
                    parts = line.split('/', 1)
                    if len(parts) == 2:
                        name_desc = parts[1].split(' ', 1)
                        pkgs.append((name_desc[0], name_desc[1] if len(name_desc) > 1 else ''))
            return pkgs
        return []
    
    def get_info(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['apt-cache', 'show', package], capture_output=True, text=True, timeout=15)
            desc = ''
            for line in result.stdout.split('\n'):
                if line.startswith('Description:'):
                    desc = line.replace('Description:', '').strip()
                    break
            return desc
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'info', package], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'Description :' in line:
                    return line.split(':', 1)[1].strip()
            return ''
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Si', package], capture_output=True, text=True, timeout=15)
            for line in result.stdout.split('\n'):
                if 'Description' in line:
                    return line.split(':', 1)[1].strip()
            return ''
        return ''
    
    def is_installed(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
            return 'ii' in result.stdout
        elif self.pm == 'dnf':
            result = subprocess.run(['rpm', '-q', package], capture_output=True)
            return result.returncode == 0
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Q', package], capture_output=True)
            return result.returncode == 0
        return False
    
    def install(self, package):
        if self.pm == 'apt':
            cmd = ['sudo', 'apt', 'install', '-y', package]
        elif self.pm == 'dnf':
            cmd = ['sudo', 'dnf', 'install', '-y', package]
        elif self.pm == 'pacman':
            cmd = ['sudo', 'pacman', '-S', '--noconfirm', package]
        else:
            return False, "No package manager"
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output.append(line.strip())
        return process.returncode == 0, '\n'.join(output[-50:])
    
    def get_pm_name(self):
        names = {'apt': 'APT (Debian/Ubuntu)', 'dnf': 'DNF (Fedora)', 'pacman': 'Pacman (Arch)'}
        return names.get(self.pm, self.pm or 'Unknown')


CATEGORIES = {
    'Tools': ['64tass', 'a56', 'cc65', 'retoroute', 'stella', 'mame', 'dosbox', 'fceux', 'vice', 'basilisk', 'sheep-shaver', 'wine', 'playonlinux', 'qemu', 'virtualbox', 'bochs', 'dosemu', '汇编器', 'asm', 'assembler', 'emulator', '模拟器'],
    'Apps': ['chromium', 'chrome', 'firefox', 'code', 'vscode', 'sublime', 'vlc', 'gimp', 'inkscape', 'blender', 'audacity', 'obs', 'discord', 'steam', ' libreoffice', 'office', 'ssh', 'vim', 'nano', 'htop', 'git', 'docker', 'nodejs', 'python', 'ruby', 'rustc', 'golang']
}

TOOL_TIPS = {
    '64tass': '6502 assembler',
    'a56': 'DSP56001 assembler', 
    'cc65': '6502 C compiler',
    'chromium': 'Web browser',
    'qemu': 'System emulator',
    'dosbox': 'DOS emulator',
    'code': 'Visual Studio Code',
}


class PackageInstallerUI:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.pm = PackageManager()
        self.packages = []
        self.search_query = ''
        self.current_idx = 0
        self.start_idx = 0
        self.category_idx = 0
        self.categories = ['All', 'Tools', 'Apps']
        self.mode = 'search'
        self.selected_pkg = None
        self.selected_category = 'All'
        self.message = ''
        self.message_time = 0
        self.searching = False
        self.search_results = []
        self.last_search = ''
        self.search_delay = 0.3
        self.last_key_time = 0
        curses.curs_set(0)
    
    def resize(self):
        self.height, self.width = self.stdscr.getmaxyx()
    
    def draw(self):
        self.resize()
        self.stdscr.clear()
        
        self._draw_header()
        self._draw_category_bar()
        self._draw_search_bar()
        
        if self.mode == 'search':
            self._draw_package_list()
        elif self.mode == 'details':
            self._draw_details()
        
        self._draw_status_bar()
        self.stdscr.refresh()
    
    def _draw_header(self):
        try:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(0, 0, '╔' + '═' * (self.width - 2) + '╗')
            title = f' Package Installer - {self.pm.get_pm_name()} '
            self.stdscr.addstr(1, (self.width - len(title)) // 2, title)
            self.stdscr.addstr(2, 0, '╚' + '═' * (self.width - 2) + '╝')
            self.stdscr.attroff(curses.color_pair(1))
        except curses.error:
            pass
    
    def _draw_category_bar(self):
        try:
            x = 2
            for i, cat in enumerate(self.categories):
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
            self.stdscr.addstr(5, 10, self.search_query + '_')
            if self.searching:
                self.stdscr.addstr(5, 10 + len(self.search_query), ' (searching...)')
        except curses.error:
            pass
    
    def _draw_package_list(self):
        try:
            list_y = 7
            max_items = self.height - list_y - 2
            
            if not self.search_results:
                self.stdscr.addstr(list_y, 2, 'Type to search for packages...')
                self.stdscr.addstr(list_y + 2, 2, 'Use arrow keys to navigate, Enter to select')
                return
            
            for i in range(min(max_items, len(self.search_results))):
                idx = self.start_idx + i
                if idx >= len(self.search_results):
                    break
                
                name, desc = self.search_results[idx]
                installed = self.pm.is_installed(name)
                
                y = list_y + i
                
                if idx == self.current_idx:
                    self.stdscr.attron(curses.color_pair(2))
                    self.stdscr.addstr(y, 2, '>')
                else:
                    self.stdscr.addstr(y, 2, ' ')
                
                if installed:
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(y, 4, '[✓]')
                    self.stdscr.attroff(curses.color_pair(3))
                else:
                    self.stdscr.addstr(y, 4, '[ ]')
                
                if idx == self.current_idx:
                    self.stdscr.addstr(y, 9, name[:self.width - 12])
                    self.stdscr.attroff(curses.color_pair(2))
                else:
                    self.stdscr.addstr(y, 9, name[:self.width - 12])
                
                if idx == self.current_idx and desc:
                    truncated = desc[:self.width - 15]
                    self.stdscr.addstr(y + 1, 9, truncated)
        except curses.error:
            pass
    
    def _draw_details(self):
        if not self.selected_pkg:
            return
        
        name, desc = self.selected_pkg
        installed = self.pm.is_installed(name)
        info = self.pm.get_info(name) or desc
        
        try:
            self.stdscr.addstr(7, 2, f'Package: {name}')
            status = 'INSTALLED' if installed else 'NOT INSTALLED'
            color = 3 if installed else 1
            self.stdscr.attron(curses.color_pair(color))
            self.stdscr.addstr(8, 2, f'Status: {status}')
            self.stdscr.attroff(curses.color_pair(color))
            
            self.stdscr.addstr(10, 2, 'Description:')
            y = 11
            words = info.split()
            line = ''
            for word in words:
                if len(line) + len(word) + 1 < self.width - 4:
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
            self.stdscr.addstr(self.height - 4, 20, '< Press Enter >')
        except curses.error:
            pass
    
    def _draw_status_bar(self):
        try:
            if self.message and time.time() - self.message_time < 3:
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(self.height - 2, 2, self.message[:self.width - 4])
                self.stdscr.attroff(curses.color_pair(3))
            
            status = f' {len(self.search_results)} packages | ↑↓ Navigate | Enter: Select/Details | Tab: Back | Ctrl+C: Quit '
            self.stdscr.addstr(self.height - 1, 0, status[:self.width])
        except curses.error:
            pass
    
    def show_message(self, msg):
        self.message = msg
        self.message_time = time.time()
    
    def handle_input(self, key):
        now = time.time()
        if now - self.last_key_time < 0.05:
            return
        self.last_key_time = now
        
        if self.mode == 'search':
            self._handle_search_input(key)
        elif self.mode == 'details':
            self._handle_details_input(key)
    
    def _handle_search_input(self, key):
        if key == curses.KEY_UP:
            if self.current_idx > 0:
                self.current_idx -= 1
                if self.current_idx < self.start_idx:
                    self.start_idx -= 1
        elif key == curses.KEY_DOWN:
            if self.current_idx < len(self.search_results) - 1:
                self.current_idx += 1
                if self.current_idx >= self.start_idx + self.height - 12:
                    self.start_idx += 1
        elif key == curses.KEY_LEFT:
            if self.category_idx > 0:
                self.category_idx -= 1
                self._filter_category()
        elif key == curses.KEY_RIGHT:
            if self.category_idx < len(self.categories) - 1:
                self.category_idx += 1
                self._filter_category()
        elif key == curses.KEY_ENTER or key == 10:
            if self.search_results:
                self.selected_pkg = self.search_results[self.current_idx]
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
            self.search_results = []
    
    def _handle_details_input(self, key):
        if key == curses.KEY_ENTER or key == 10:
            if self.selected_pkg:
                pkg_name = self.selected_pkg[0]
                if self.pm.is_installed(pkg_name):
                    self.show_message('Use system package manager to uninstall')
                else:
                    success, output = self.pm.install(pkg_name)
                    if success:
                        self.show_message(f'{pkg_name} installed!')
                    else:
                        self.show_message('Installation failed')
                    self.mode = 'search'
        elif key == 9 or key == curses.KEY_LEFT or key == curses.KEY_ESCAPE or key == 27:
            self.mode = 'search'
    
    def _filter_category(self):
        cat = self.categories[self.category_idx]
        if cat == 'All':
            self.selected_category = 'All'
        else:
            self.selected_category = cat
        self._do_search()
    
    def _do_search(self):
        if len(self.search_query) < 1:
            self.search_results = []
            return
        
        self.searching = True
        
        terms = self.search_query.lower().split()
        all_results = self.pm.search(self.search_query)
        
        filtered = []
        for name, desc in all_results:
            name_lower = name.lower()
            desc_lower = desc.lower()
            
            cat_match = True
            if self.selected_category != 'All':
                if self.selected_category == 'Tools':
                    cat_match = any(t.lower() in name_lower or t.lower() in desc_lower for t in CATEGORIES['Tools'])
                elif self.selected_category == 'Apps':
                    cat_match = any(a.lower() in name_lower or a.lower() in desc_lower for a in CATEGORIES['Apps'])
            
            if cat_match:
                score = 0
                for term in terms:
                    if term in name_lower:
                        score += 10
                    if term in desc_lower:
                        score += 1
                if score > 0:
                    filtered.append((name, desc, score))
        
        filtered.sort(key=lambda x: -x[2])
        self.search_results = [(n, d) for n, d, s in filtered]
        self.current_idx = min(self.current_idx, len(self.search_results) - 1) if self.search_results else 0
        self.start_idx = 0
        self.searching = False


def main(stdscr):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    
    stdscr.keypad(True)
    stdscr.nodelay(True)
    stdscr.timeout(100)
    
    pm = PackageManager()
    if pm.pm is None:
        stdscr.addstr(0, 0, 'No supported package manager found!')
        stdscr.getch()
        return
    
    try:
        pm.update_cache()
    except:
        pass
    
    ui = PackageInstallerUI(stdscr)
    
    while True:
        ui.draw()
        key = ui.stdscr.getch()
        if key == 3:
            break
        if key != -1:
            ui.handle_input(key)


if __name__ == '__main__':
    curses.wrapper(main)