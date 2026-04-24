#!/usr/bin/env python3
import sys
import subprocess
import os
import time

try:
    import curses
except ImportError:
    print("curses module not available. Please run in a proper terminal.")
    sys.exit(1)

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
        else:
            return None
    
    def update_cache(self):
        if self.pm == 'apt':
            subprocess.run(['sudo', 'apt', 'update'], capture_output=True)
        elif self.pm == 'dnf':
            subprocess.run(['sudo', 'dnf', 'check-update'], capture_output=True)
        elif self.pm == 'pacman':
            subprocess.run(['sudo', 'pacman', '-Sy'], capture_output=True)
        elif self.pm == 'zypper':
            subprocess.run(['sudo', 'zypper', 'refresh'], capture_output=True)
        elif self.pm == 'xbps':
            subprocess.run(['sudo', 'xbps-install', '-S'], capture_output=True)
        elif self.pm == 'apk':
            subprocess.run(['sudo', 'apk', 'update'], capture_output=True)
    
    def search(self, query):
        if self.pm == 'apt':
            result = subprocess.run(['apt-cache', 'search', query], capture_output=True, text=True)
            return [line.split(' - ', 1) for line in result.stdout.strip().split('\n') if line]
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'search', query], capture_output=True, text=True)
            return self._parse_dnf_search(result.stdout)
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Ss', query], capture_output=True, text=True)
            return self._parse_pacman_search(result.stdout)
        elif self.pm == 'zypper':
            result = subprocess.run(['zypper', 'search', query], capture_output=True, text=True)
            return self._parse_zypper_search(result.stdout)
        elif self.pm == 'xbps':
            result = subprocess.run(['xbps-query', '-Rs', query], capture_output=True, text=True)
            return self._parse_xbps_search(result.stdout)
        elif self.pm == 'apk':
            result = subprocess.run(['apk', 'search', query], capture_output=True, text=True)
            return [(line, '') for line in result.stdout.strip().split('\n') if line]
        return []
    
    def _parse_dnf_search(self, output):
        packages = []
        for line in output.split('\n'):
            if line.startswith('Last metadata') or line.startswith('=') or not line.strip():
                continue
            parts = line.split(':', 2)
            if len(parts) >= 2:
                packages.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ''))
        return packages
    
    def _parse_pacman_search(self, output):
        packages = []
        for line in output.split('\n'):
            if line.startswith('[') or not line.strip():
                continue
            if ' :: ' in line:
                line = line.split(' :: ', 1)[1]
            parts = line.split('/', 1)
            if len(parts) == 2:
                name_desc = parts[1].split(' ', 1)
                name = name_desc[0]
                desc = name_desc[1] if len(name_desc) > 1 else ''
                packages.append((name, desc))
        return packages
    
    def _parse_zypper_search(self, output):
        packages = []
        for line in output.split('\n'):
            if line.startswith('S |') or line.startswith('-') or not line.strip():
                continue
            parts = line.split('|', 2)
            if len(parts) >= 3:
                packages.append((parts[1].strip(), parts[2].strip()))
        return packages
    
    def _parse_xbps_search(self, output):
        packages = []
        for line in output.split('\n'):
            if ' - ' in line:
                parts = line.split(' - ', 1)
                packages.append((parts[0].strip(), parts[1].strip() if len(parts) > 1 else ''))
        return packages
    
    def get_info(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['apt-cache', 'show', package], capture_output=True, text=True)
            return self._parse_apt_info(result.stdout)
        elif self.pm == 'dnf':
            result = subprocess.run(['dnf', 'info', package], capture_output=True, text=True)
            return self._parse_dnf_info(result.stdout)
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Si', package], capture_output=True, text=True)
            return result.stdout
        elif self.pm == 'zypper':
            result = subprocess.run(['zypper', 'info', package], capture_output=True, text=True)
            return result.stdout
        elif self.pm == 'xbps':
            result = subprocess.run(['xbps-query', '-R', '-i', package], capture_output=True, text=True)
            return result.stdout
        elif self.pm == 'apk':
            result = subprocess.run(['apk', 'info', '-a', package], capture_output=True, text=True)
            return result.stdout
        return ''
    
    def _parse_apt_info(self, output):
        desc = ''
        for line in output.split('\n'):
            if line.startswith('Description:'):
                desc = line.replace('Description:', '').strip()
                break
        return desc
    
    def _parse_dnf_info(self, output):
        desc = ''
        for line in output.split('\n'):
            if line.startswith('Description :'):
                desc = line.replace('Description :', '').strip()
                break
        return desc
    
    def is_installed(self, package):
        if self.pm == 'apt':
            result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True)
            return 'ii' in result.stdout
        elif self.pm == 'dnf':
            result = subprocess.run(['rpm', '-q', package], capture_output=True, text=True)
            return result.returncode == 0
        elif self.pm == 'pacman':
            result = subprocess.run(['pacman', '-Q', package], capture_output=True, text=True)
            return result.returncode == 0
        elif self.pm == 'zypper':
            result = subprocess.run(['rpm', '-q', package], capture_output=True, text=True)
            return result.returncode == 0
        elif self.pm == 'xbps':
            result = subprocess.run(['xbps-query', '-m', package], capture_output=True, text=True)
            return result.returncode == 0
        elif self.pm == 'apk':
            result = subprocess.run(['apk', 'info', package], capture_output=True, text=True)
            return result.returncode == 0
        return False
    
    def install(self, package, progress_callback=None):
        if self.pm == 'apt':
            cmd = ['sudo', 'apt', 'install', '-y', package]
        elif self.pm == 'dnf':
            cmd = ['sudo', 'dnf', 'install', '-y', package]
        elif self.pm == 'pacman':
            cmd = ['sudo', 'pacman', '-S', '--noconfirm', package]
        elif self.pm == 'zypper':
            cmd = ['sudo', 'zypper', 'install', '-y', package]
        elif self.pm == 'xbps':
            cmd = ['sudo', 'xbps-install', '-y', package]
        elif self.pm == 'apk':
            cmd = ['sudo', 'apk', 'add', package]
        else:
            return False, "No package manager found"
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                output_lines.append(line.strip())
                if progress_callback:
                    progress_callback(line.strip())
        
        success = process.returncode == 0
        return success, '\n'.join(output_lines)
    
    def get_pm_name(self):
        names = {
            'apt': 'APT (Debian/Ubuntu)',
            'dnf': 'DNF (Fedora/RHEL)',
            'pacman': 'Pacman (Arch)',
            'zypper': 'Zypper (openSUSE)',
            'xbps': 'XBPS (Void)',
            'apk': 'APK (Alpine)'
        }
        return names.get(self.pm, self.pm or 'Unknown')


class PackageInstallerUI:
    def __init__(self, stdscr, pm):
        self.stdscr = stdscr
        self.pm = pm
        self.packages = []
        self.search_query = ''
        self.current_idx = 0
        self.start_idx = 0
        self.selected_idx = None
        self.installing = False
        self.install_status = ''
        self.install_progress = 0
        self.install_output = []
        self.mode = 'search'
        self.message = ''
        self.message_time = 0
    
    def resize(self):
        self.height, self.width = self.stdscr.getmaxyx()
    
    def show_message(self, msg):
        self.message = msg
        self.message_time = time.time()
    
    def draw(self):
        self.resize()
        self.stdscr.clear()
        try:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(0, 0, '┌' + '─' * (self.width - 2) + '┐')
            self.stdscr.addstr(1, 2, f' Package Installer - {self.pm.get_pm_name()} ')
            self.stdscr.addstr(2, 0, '└' + '─' * (self.width - 2) + '┘')
            self.stdscr.attroff(curses.color_pair(1))
        except curses.error:
            pass
        
        if self.mode == 'search':
            self._draw_search()
        elif self.mode == 'details':
            self._draw_details()
        
        if self.message and time.time() - self.message_time < 3:
            self.stdscr.attron(curses.color_pair(3))
            try:
                self.stdscr.addstr(self.height - 2, 2, self.message[:self.width - 4])
            except curses.error:
                pass
            self.stdscr.attroff(curses.color_pair(3))
        
        status_text = ' ↑↓ Navigate | Enter: Select | Tab: Switch | Ctrl+C: Quit '
        self.stdscr.addstr(self.height - 1, 0, status_text[:self.width])
        self.stdscr.refresh()
    
    def _draw_search(self):
        input_y = 4
        self.stdscr.addstr(input_y, 2, f'Search: {self.search_query}')
        self.stdscr.addstr(input_y, 10 + len(self.search_query), '█')
        
        if not self.packages:
            self.stdscr.addstr(input_y + 2, 2, 'Type to search for packages...')
            return
        
        list_start = input_y + 2
        max_items = self.height - list_start - 4
        
        for i in range(min(max_items, len(self.packages))):
            idx = self.start_idx + i
            if idx >= len(self.packages):
                break
            
            pkg = self.packages[idx]
            name, desc = pkg[0], pkg[1] if len(pkg) > 1 else ''
            installed = self.pm.is_installed(name)
            
            if idx == self.current_idx:
                self.stdscr.attron(curses.color_pair(2))
            
            if installed:
                self.stdscr.addstr(list_start + i, 2, '✓ ')
            else:
                self.stdscr.addstr(list_start + i, 2, '  ')
            
            self.stdscr.addstr(list_start + i, 4, name[:self.width - 6])
            if idx == self.current_idx:
                self.stdscr.attroff(curses.color_pair(2))
    
    def _draw_details(self):
        if self.selected_idx is None or self.selected_idx >= len(self.packages):
            return
        
        pkg = self.packages[self.selected_idx]
        name, desc = pkg[0], pkg[1] if len(pkg) > 1 else ''
        installed = self.pm.is_installed(name)
        info = self.pm.get_info(name)
        if not desc:
            desc = info
        
        self.stdscr.addstr(4, 2, f'Package: {name}')
        self.stdscr.addstr(5, 2, f'Status: {"Installed" if installed else "Not installed"}')
        
        y = 7
        self.stdscr.addstr(y, 2, 'Description:')
        y += 1
        desc_lines = self._wrap_text(desc, self.width - 6)
        for line in desc_lines[:self.height - y - 6]:
            self.stdscr.addstr(y, 4, line)
            y += 1
        
        if self.installing:
            self._draw_install_progress()
        else:
            install_y = self.height - 6
            if installed:
                self.stdscr.addstr(install_y, 2, '[ Uninstall ]')
            else:
                self.stdscr.addstr(install_y, 2, '[ Install ]')
            self.stdscr.addstr(install_y, 16, '< Press Enter >')
    
    def _draw_install_progress(self):
        install_y = self.height - 8
        self.stdscr.addstr(install_y, 2, 'Installing...')
        
        bar_width = self.width - 20
        filled = int(self.install_progress * bar_width)
        bar = '█' * filled + '░' * (bar_width - filled)
        self.stdscr.addstr(install_y + 1, 2, f'[{bar}] {int(self.install_progress * 100)}%')
        
        for i, line in enumerate(self.install_output[-5:]):
            self.stdscr.addstr(install_y + 3 + i, 2, line[:self.width - 4])
        
        if self.install_status:
            self.stdscr.addstr(install_y + 8, 2, self.install_status)
    
    def _wrap_text(self, text, width):
        import textwrap
        return textwrap.wrap(text, width)
    
    def handle_input(self, key):
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
            if self.current_idx < len(self.packages) - 1:
                self.current_idx += 1
                if self.current_idx >= self.start_idx + self.height - 10:
                    self.start_idx += 1
        elif key == curses.KEY_ENTER or key == 10:
            if self.packages:
                self.selected_idx = self.current_idx
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
            self.packages = []
    
    def _handle_details_input(self, key):
        if key == curses.KEY_ENTER or key == 10:
            if not self.installing and self.selected_idx is not None:
                pkg_name = self.packages[self.selected_idx][0]
                installed = self.pm.is_installed(pkg_name)
                if installed:
                    self.show_message(f'To remove {pkg_name}, use your package manager directly')
                else:
                    self._start_install(pkg_name)
        elif key == 9 or key == curses.KEY_LEFT or key == curses.KEY_RIGHT:
            self.mode = 'search'
            self.installing = False
        elif key == 27:
            self.mode = 'search'
            self.installing = False
    
    def _do_search(self):
        if len(self.search_query) >= 2:
            self.packages = self.pm.search(self.search_query)
            self.current_idx = 0
            self.start_idx = 0
        elif not self.search_query:
            self.packages = []
    
    def _start_install(self, package):
        self.installing = True
        self.install_progress = 0
        self.install_output = []
        
        def progress_callback(line):
            self.install_output.append(line)
            if len(self.install_output) > 100:
                self.install_output = self.install_output[-50:]
            
            if 'Reading' in line or 'Resolving' in line or 'Building' in line:
                self.install_progress = min(self.install_progress + 0.1, 0.9)
            elif '%' in line:
                import re
                match = re.search(r'(\d+)%', line)
                if match:
                    self.install_progress = int(match.group(1)) / 100 * 0.9
            
            self.stdscr.timeout(50)
            self.draw()
        
        success, result = self.pm.install(package, progress_callback)
        self.install_progress = 1.0
        self.install_status = '✓ Installed successfully!' if success else '✗ Installation failed'
        self.show_message(self.install_status)
        self.installing = False


def main(stdscr):
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_RED)
    
    stdscr.keypad(True)
    stdscr.timeout(100)
    
    pm = PackageManager()
    
    if pm.pm is None:
        stdscr.addstr(0, 0, 'No supported package manager found!')
        stdscr.getch()
        return
    
    pm.update_cache()
    
    ui = PackageInstallerUI(stdscr, pm)
    
    while True:
        ui.draw()
        key = stdscr.getch()
        if key == 3:
            break
        ui.handle_input(key)


if __name__ == '__main__':
    curses.wrapper(main)