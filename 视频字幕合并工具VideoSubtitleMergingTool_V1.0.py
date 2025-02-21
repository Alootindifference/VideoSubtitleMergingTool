import os
import subprocess
import sys
import threading
from tkinter import *
from tkinter import ttk, filedialog, messagebox

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

class SubtitleMerger:
    def __init__(self, root):
        self.root = root
        self.root.title("字幕合并工具V1.0")
        self.setup_ui()

        # 初始化变量
        self.video_files = []
        self.subtitle_files = []
        self.output_dir = ""
        self.running = False
        self.progress_value = 0

    def setup_ui(self):
        # 文件选择区域
        frame = ttk.Frame(self.root, padding=10)
        frame.grid(row=0, column=0, sticky=(W, E))

        # 单个文件处理
        ttk.Button(frame, text="选择视频文件", command=self.select_video).grid(row=0, column=0, sticky=W)
        self.video_path = ttk.Entry(frame, width=50)
        self.video_path.grid(row=0, column=1, padx=5)

        ttk.Button(frame, text="选择字幕文件", command=self.select_subtitle).grid(row=1, column=0, sticky=W)
        self.sub_path = ttk.Entry(frame, width=50)
        self.sub_path.grid(row=1, column=1, padx=5)

        # 批量处理
        ttk.Button(frame, text="批量选择视频目录", command=self.select_video_dir).grid(row=2, column=0, sticky=W)
        self.video_dir = ttk.Entry(frame, width=50)
        self.video_dir.grid(row=2, column=1, padx=5)

        ttk.Button(frame, text="批量选择字幕目录", command=self.select_sub_dir).grid(row=3, column=0, sticky=W)
        self.sub_dir = ttk.Entry(frame, width=50)
        self.sub_dir.grid(row=3, column=1, padx=5)

        # 输出目录
        ttk.Button(frame, text="选择输出目录", command=self.select_output).grid(row=4, column=0, sticky=W)
        self.output_path = ttk.Entry(frame, width=50)
        self.output_path.grid(row=4, column=1, padx=5)

        # 进度条
        self.progress = ttk.Progressbar(frame, orient=HORIZONTAL, length=300, mode='determinate')
        self.progress.grid(row=5, column=0, columnspan=2, pady=10)
        self.percent_label = ttk.Label(frame, text="0%")
        self.percent_label.grid(row=6, column=0, columnspan=2)

        # 控制按钮
        ttk.Button(frame, text="开始处理", command=self.start_process).grid(row=7, column=0, pady=10)
        ttk.Button(frame, text="取消", command=self.cancel_process).grid(row=7, column=1, pady=10)

    def select_video(self):
        file = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.avi *.mkv")])
        self.video_path.delete(0, END)
        self.video_path.insert(0, file)

    def select_subtitle(self):
        file = filedialog.askopenfilename(filetypes=[("Subtitle files", "*.srt *.ass *.vtt")])
        self.sub_path.delete(0, END)
        self.sub_path.insert(0, file)

    def select_video_dir(self):
        directory = filedialog.askdirectory()
        self.video_dir.delete(0, END)
        self.video_dir.insert(0, directory)

    def select_sub_dir(self):
        directory = filedialog.askdirectory()
        self.sub_dir.delete(0, END)
        self.sub_dir.insert(0, directory)

    def select_output(self):
        directory = filedialog.askdirectory()
        self.output_path.delete(0, END)
        self.output_path.insert(0, directory)

    def start_process(self):
        if self.running:
            return

        # 获取输出目录
        self.output_dir = self.output_path.get()
        if not self.output_dir:
            messagebox.showerror("错误", "请先选择输出目录")
            return

        # 处理模式判断
        if self.video_path.get() and self.sub_path.get():
            self.process_single()
        elif self.video_dir.get() and self.sub_dir.get():
            self.process_batch()
        else:
            messagebox.showerror("错误", "请选择文件或目录")

    def process_single(self):
        video = self.video_path.get()
        sub = self.sub_path.get()
        if not (video and sub):
            return

        self.video_files = [video]
        self.subtitle_files = [sub]
        threading.Thread(target=self.run_ffmpeg_tasks).start()

    def process_batch(self):
        video_dir = self.video_dir.get()
        sub_dir = self.sub_dir.get()

        self.video_files = self._get_valid_files(video_dir, ['mp4', 'avi', 'mkv', 'mov'])
        self.subtitle_files = self._get_valid_files(sub_dir, ['srt', 'ass', 'vtt', 'ssa'])

        # 智能匹配文件（新增方法）
        matched_pairs = self._match_files(self.video_files, self.subtitle_files)

        if not matched_pairs:
            messagebox.showerror("错误", "找不到可匹配的视频字幕组合")
            return

        #if len(self.video_files) != len(self.subtitle_files):
            #messagebox.showerror("错误", "视频和字幕文件数量不匹配")
            #return

        # 使用匹配后的文件列表
        self.video_files = [pair[0] for pair in matched_pairs]
        self.subtitle_files = [pair[1] for pair in matched_pairs]

        threading.Thread(target=self.run_ffmpeg_tasks).start()

    def _get_valid_files(self, directory, extensions):
        """获取目录中指定扩展名的有效文件（排除隐藏文件）"""
        return sorted([
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if (f.lower().endswith(tuple(extensions))
                and not f.startswith('.')
                and os.path.isfile(os.path.join(directory, f)))
        ], key=lambda x: os.path.splitext(os.path.basename(x))[0])

    def _match_files(self, videos, subs):
        """智能匹配视频和字幕文件"""
        matched = []
        unmatched_videos = []
        unmatched_subs = subs.copy()

        # 第一阶段：精确匹配（主文件名完全一致）
        for v in videos:
            base = os.path.splitext(os.path.basename(v))[0]
            for s in subs:
                sub_base = os.path.splitext(os.path.basename(s))[0]
                if base == sub_base:
                    matched.append((v, s))
                    if s in unmatched_subs:
                        unmatched_subs.remove(s)
                    break
            else:
                unmatched_videos.append(v)

        # 第二阶段：模糊匹配（尝试数字序列匹配）
        for v in unmatched_videos:
            base = self._extract_number_pattern(os.path.basename(v))
            if not base:
                continue

            for s in unmatched_subs:
                sub_base = self._extract_number_pattern(os.path.basename(s))
                if base == sub_base:
                    matched.append((v, s))
                    unmatched_subs.remove(s)
                    break

        # 第三阶段：顺序匹配（剩余文件按排序匹配）
        min_length = min(len(unmatched_videos), len(unmatched_subs))
        if min_length > 0:
            matched += list(zip(
                unmatched_videos[:min_length],
                unmatched_subs[:min_length]
            ))

        return matched

    def _extract_number_pattern(self, filename):
        """提取文件名中的数字特征（用于模糊匹配）"""
        # 示例：将 "Episode01" -> "01", "S02E03" -> "0203"
        numbers = ''.join(filter(str.isdigit, filename))
        return numbers if numbers else None

    def run_ffmpeg_tasks(self):
        self.running = True
        total = len(self.video_files)

        for i, (video, sub) in enumerate(zip(self.video_files, self.subtitle_files)):
            output = os.path.join(self.output_dir, f"output_{os.path.basename(video)}")

            # 强制使用UTF-8编码处理文件路径
            video = os.fsdecode(video.encode('utf-8'))
            sub = os.fsdecode(sub.encode('utf-8'))
            output = os.fsdecode(output.encode('utf-8'))

            cmd = [
                'ffmpeg',
                '-i', video,
                '-i', sub,
                '-c', 'copy',
                '-c:s', 'mov_text',
                '-map', '0',
                '-map', '1',
                output
            ]

            try:
                process = subprocess.Popen(
                    cmd,
                    stderr=subprocess.STDOUT,
                    stdout=subprocess.PIPE,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )

                while True:
                    output_line = process.stdout.readline()
                    if output_line == '' and process.poll() is not None:
                        break
                    if 'time=' in output_line:
                        # 这里可以添加更精确的进度解析
                        self.update_progress((i + 1) * 100 // total)

                if process.returncode != 0:
                    self.show_error(f"处理失败: {os.path.basename(video)}")
                else:
                    self.show_success(f"处理成功: {os.path.basename(video)}")

            except Exception as e:
                self.show_error(str(e))

        self.running = False
        messagebox.showinfo("完成", "所有任务处理完成")

    def update_progress(self, value):
        self.progress_value = value
        self.root.after(10, self._update_ui)

    def _update_ui(self):
        self.progress['value'] = self.progress_value
        self.percent_label.config(text=f"{self.progress_value}%")

    def show_success(self, msg):
        self.root.after(10, lambda: messagebox.showinfo("成功", msg))

    def show_error(self, msg):
        self.root.after(10, lambda: messagebox.showerror("错误", msg))

    def cancel_process(self):
        self.running = False
        messagebox.showinfo("信息", "操作已取消")


if __name__ == "__main__":
    root = Tk()
    app = SubtitleMerger(root)
    root.mainloop()