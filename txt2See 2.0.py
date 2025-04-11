import os
import shutil
import cv2
import tkinter as tk
from tkinter import filedialog, ttk,messagebox
from PIL import Image, ImageTk
import numpy as np
from tkinter.simpledialog import askstring

class ImageLabeler:
    def __init__(self, root):
        self.root = root
        self.root.title("txt2See v2.0")
        self.root.geometry("800x600")
        
        # icon_path = r"G:\ico\txt.png"
        # icon_image = Image.open(icon_path)
        # icon_photo = ImageTk.PhotoImage(icon_image)
        # self.root.iconphoto(False, icon_photo)
        
        # 创建菜单栏
        menu_bar = tk.Menu(root)
        root.config(menu=menu_bar)

        # 添加 'File' 菜单
        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.load_folder)
        file_menu.add_command(label="Save", command=self.save_image)

        # 添加 'Help' 菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About",command=self.show_instructions)
        
        # UI组件
        # 创建画布
        self.canvas = tk.Canvas(root, bg="white")
        self.canvas.pack(expand=True)
#         self.canvas = tk.Canvas(root, bg="white",width=800, height=800)
#         self.canvas.pack()
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        
       # 创建用于控制文本可见性的 Checkbutton
        self.show_text_var = tk.BooleanVar(value=True)
        toggle_button = tk.Checkbutton(root, text="Show Text", variable=self.show_text_var, command=self.toggle_text_visibility)
        toggle_button.pack()
        
        self.label_type_var = tk.StringVar()
        self.label_type_dropdown = ttk.Combobox(self.root, textvariable=self.label_type_var, state='readonly')
        self.label_type_dropdown['values'] = ('bbox', 'kpt', 'seg')
        self.label_type_dropdown.current(0)
        self.label_type_dropdown.pack()
        
        self.status_label = tk.Label(self.root, text="第 0 张 / 共 0 张")
        self.status_label.pack(pady=10)
        
        
        # 创建右键菜单
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="浏览模式", command=self.Disable_modification)
        self.context_menu.add_command(label="编辑模式", command=self.enable_modification)
        self.context_menu.add_command(label="删除模式", command=self.enable_deleting)
        self.context_menu.add_command(label="插入关键点", command=self.enable_inserting)
        self.context_menu.add_command(label="插入矩形", command=self.enable_insertingRect)
        
        # 初始化变量
        self.imagespath = ""
        self.labelspath = ""
        self.newimagespath = ""
        self.newlabelspath = ""
        self.image_files = []
        self.current_index = 0
        self.img_width = 0
        self.img_height = 0
        self.handles=[]
        self.dragging_handle = None
        self.first_category_id=None
        self.keypoint_count=0
        self.is_modifying = False  # 标记是否允许拖拽
        self.is_inserting = False  # 标记是否允许拖拽
        self.is_insertingRect = False
        self.is_deleting =False
        self.is_changed  =False
        self.is_dragging = False
        self.current_rect=None
        self.image_path=None
        
        #缩放因子  默认为1
        self.scale_factor=1

        
       # 保存原始位置的数据结构
        self.data = {}
        
        self.start_x = None
        self.start_y = None
        
        self.text2oval = {}  # Dictionary to store tag to ids mapping
        self.oval2text = {}
        self.text2rect={}
        self.rect2text = {}
        self.index=0
        self.color_list=None
        
        # 绑定事件
        self.canvas.bind('<Button-1>', self.on_canvas_click)
        self.canvas.bind('<Button-3>', self.on_canvas_right_click)
        
#         self.load_button = tk.Button(self.root, text="加载图像文件夹", command=self.load_folder)
#         self.load_button.pack(pady=10)
#         self.load_button = tk.Button(self.root, text="导出", command=self.save_canvas_to_yolo)
#         self.load_button.pack(pady=10)
        
        # 绑定事件
        self.root.bind('<Right>', self.next_image)
        self.root.bind('<Left>', self.prev_image)
        self.root.bind('<s>', self.save_image)
        self.root.bind('<d>', self.delete_image)
    
    #模式部分
    def enable_deleting(self):
        self.is_modifying = False
        self.is_inserting = False
        self.is_insertingRect = False
        self.is_deleting= True
        self.current_rect=None
        self.is_changed=True
        
    def enable_modification(self):
        self.is_modifying = True
        self.is_inserting = False
        self.is_deleting= False
        self.is_insertingRect = False
        self.current_rect=None
        self.is_changed=True
        
    def enable_insertingRect(self):
        self.is_modifying = False
        self.is_inserting =False
        self.is_deleting= False
        self.is_insertingRect = True
        self.current_rect=None
        self.is_changed=True
        
    def enable_inserting(self):
        self.is_modifying = False
        self.is_inserting = True
        self.is_deleting= False
        self.is_insertingRect = False
        self.current_rect=None
        self.is_changed=True
        
    def Disable_modification(self):
        self.is_modifying = False
        self.is_inserting =False
        self.is_deleting=False
        self.is_insertingRect = False
        self.current_rect=None
    
    
    
    # 右键
    def on_canvas_right_click(self, event):
        self.context_menu.post(event.x_root, event.y_root)
    
    #通用
    def show_instructions(self):
        instructions = (
            "欢迎使用txt标签查看器！\n\n"
            "v1.0功能包含:\n"
            "快速查看图像标签情况+对图像标签筛选到新文件夹！\n"
            "使用说明:\n"
            "1. 点击 '加载图像文件夹' 按钮选择图像文件夹。\n"
            "2. 使用方向键左右键浏览图像。\n"
            "3. 按 's' 键保存图像和标签。\n"
            "4. 按 'd' 键删除图像和标签。\n"
            "5. 从下拉菜单中选择标签类型 (bbox, kpt, seg)。\n"
            "v2.0功能包含:\n"
            "1.增删改:右键选择模式\n"
            "2.图片缩放：未修改前可以进行图片缩放\n"
            "3.文字隐藏：开关控制文字是否显示\n\n"
            "数据格式为\n"
            "---root\n"
                "-----images\n"
                "-----labels\n"
            
            "按 '确定' 开始使用。"
        )
        messagebox.showinfo("使用说明", instructions)  
        
    def find_available_tag(self, existing_tags):
        # Find an available tag that is not in the existing tags
        for j in range(self.index):
            for i in range(self.keypoint_count):
                tag =str(j)+"_"+str(i)
                if tag not in existing_tags[j]:
                    return tag
        return None

    def mkdir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
            print('文件夹创建成功：', path)
        else:
            print('文件夹已经存在：', path)
            
    def toggle_text_visibility(self):
        """切换文本对象的可见性"""
        all_items = self.canvas.find_all()
        for item_id in all_items:
            if self.canvas.type(item_id)=="text":
                if self.show_text_var.get():
                    self.canvas.itemconfigure(item_id, state=tk.NORMAL)
                else:
                    self.canvas.itemconfigure(item_id, state=tk.HIDDEN)     
                    
    def auto_close_messagebox(self, message, duration=1000):
        top = tk.Toplevel(self.root)
        top.title("提示")
        top.geometry("200x100")
        tk.Label(top, text=message).pack(expand=True)
        top.after(duration, top.destroy)
        
    def clip_event_coords_to_image_bounds(self,event,canvas, image_width, image_height):
        """
        将鼠标事件坐标限制在图像的有效范围内，并计算 Canvas 上图像的偏移量。

        参数:
        event_x: 鼠标事件的 x 坐标。
        event_y: 鼠标事件的 y 坐标。
        canvas: 当前的 Canvas 对象。
        image_width: 图像的宽度。
        image_height: 图像的高度。

        返回:
        限制在图像范围内的坐标 (x, y)，如果超出边界则输出警告信息。
        """
        event_x=event.x
        event_y=event.y
        # 获取 Canvas 尺寸
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
#         print(canvas_width ,canvas_height)
        # 计算 Canvas 中图像的偏移量
        img_x_offset = (canvas_width - image_width) / 2
        img_y_offset = (canvas_height - image_height) / 2
#         print(img_x_offset,img_y_offset)
        # 将事件坐标转换为 Canvas 上图像的坐标
        x_img = event_x - img_x_offset
        y_img = event_y - img_y_offset
#         print("imgx",image_width)
#         print(image_height)
#         print("x_img",x_img)
#         print(y_img)
        # 限制坐标在图像的边界内
        x_img = max(0, min(x_img, image_width - 1))
        y_img = max(0, min(y_img, image_height - 1))
        
#         print("imgx",image_width)
#         print(image_height)
#         print("x_img",x_img)
#         print(y_img)
        # 计算限制后的 Canvas 坐标
        x_canvas = x_img + img_x_offset
        y_canvas = y_img + img_y_offset

        return (x_canvas, y_canvas)
    
    
    def load_folder(self):
        path = filedialog.askdirectory(title="选择图像文件夹")
        if path:
            self.imagespath = os.path.join(path, "images")
            self.labelspath = os.path.join(path, "labels")
            self.newimagespath = os.path.join(path, "newimages")
            self.newlabelspath = os.path.join(path, "newlabels")
            self.image_files = [f for f in os.listdir(self.imagespath) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
            self.current_index = 0
            self.process_image()

    def next_image(self, event=None):
        self.is_changed=False
        self.scale_factor=1
        self.Disable_modification()
        self.current_index += 1
        if self.current_index >= len(self.image_files):
            self.current_index = 0
        self.process_image()
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()

    def prev_image(self, event=None):
        self.Disable_modification()
        self.is_changed=False
        self.scale_factor=1
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = len(self.image_files) - 1
        self.process_image()
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()
        
        

    def save_image(self, event=None):
        if self.current_index < 0 or self.current_index >= len(self.image_files):
            return
        
        imagename = self.image_files[self.current_index]
        image_path = os.path.join(self.imagespath, imagename)
        label_path = os.path.join(self.labelspath, f"{os.path.splitext(imagename)[0]}.txt")
        
        new_image_path = os.path.join(self.newimagespath, imagename)
        new_label_path = os.path.join(self.newlabelspath, f"{os.path.splitext(imagename)[0]}.txt")
        
        self.mkdir(self.newimagespath)
        self.mkdir(self.newlabelspath)
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()
        if not self.is_changed:
            shutil.copy(image_path, new_image_path)
            shutil.copy(label_path, new_label_path)
            self.auto_close_messagebox("原图像和标签已保存")
        else:
            shutil.copy(image_path, new_image_path)
            self.save_canvas_to_yolo()
            self.auto_close_messagebox("新图像和新标签已保存")
            # 复原   
            
    def on_mouse_wheel(self, event):
        # Adjust the zoom factor
#         oldscale = self.scale_factor-0.1
            
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()   
#         if self.canvas.winfo_width()> 1920-50 or self.canvas.winfo_height()> 904-50:
#             self.scale_factor=oldscale
#         print(self.canvas.winfo_width(),self.canvas.winfo_height())
#         print(self.img_width,self.img_height)

#         if self.keypoint_count!=20:
#             self.auto_close_messagebox("关键点计算错误，为："+str(self.keypoint_count))

#         print(self.keypoint_count)
        if not self.is_changed:
            if event.delta > 0:
                self.scale_factor *=1.1   # Zoom in
            elif event.delta < 0:
                self.scale_factor *=0.9  # Zoom out
            self.process_image()
        else:
            self.auto_close_messagebox("已修改，不允许缩放")
            
    def process_image(self):
        if self.current_index < 0 or self.current_index >= len(self.image_files):
            return

        imagename = self.image_files[self.current_index]
        image_path = os.path.join(self.imagespath, imagename)
        label_path = os.path.join(self.labelspath, f"{os.path.splitext(imagename)[0]}.txt")

        if not os.path.exists(image_path) or not os.path.exists(label_path):
            print("图像或标签文件不存在")
            return

        picture = cv2.imread(image_path)
        self.image_path=picture
        picWidth = picture.shape[1]
        picHeight = picture.shape[0]

        # 定义颜色列表
        color_list = [
            (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 0), 
            (0, 255, 255), (255, 0, 255), (128, 0, 0), (0, 128, 0),
            (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128),
            (64, 64, 64), (192, 192, 192), (128, 128, 128), (0, 0, 64),
            (64, 0, 64), (64, 64, 0), (0, 64, 0), (0, 64, 64),
            (64, 0, 0), (192, 0, 192), (192, 192, 0), (192, 0, 0),
            (0, 192, 192), (0, 192, 0), (192, 0, 192), (192, 192, 192),
            (255, 128, 0), (128, 255, 0), (0, 255, 128), (0, 128, 255),
            (128, 0, 255), (255, 0, 128), (255, 128, 128), (128, 255, 128),
            (128, 128, 255), (255, 255, 128), (128, 255, 255), (255, 128, 255),
            (64, 128, 128), (128, 64, 128), (128, 128, 64), (64, 128, 64),
            (64, 64, 128), (128, 64, 64), (64, 64, 255), (255, 64, 64),
            (64, 255, 64), (64, 64, 192), (192, 64, 64), (64, 192, 64)
        ]
        self.color_list=color_list
        label_type = self.label_type_var.get()
        
#         if picWidth >=1920-50 or picHeight>=904-50:
#             self.scale_factor=0.5
        
        # 清空画布
        self.canvas.delete("all")

        
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()
        
        # 加载图片到画布并居中显示
        self.display_image(picture)
        
        # 计算图片在 Canvas 上的位置（居中）
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        img_width = picture.shape[1]*self.scale_factor
        img_height = picture.shape[0]*self.scale_factor
        self.img_width = picture.shape[1]*self.scale_factor
        self.img_height = picture.shape[0]*self.scale_factor
#         print("self.img_height",self.img_height)

        x_offset = (canvas_width - img_width) / 2
        y_offset = (canvas_height - img_height) / 2

        category_color_map = {}  # 字典映射类别到颜色
        self.first_category_id = None  # 记录第一个类别的ID

        with open(label_path, "r", encoding="utf-8") as f:
            data1 = f.read().split("\n")
            index=0
            self.index=0
            if len(data1[:-1]) == 0:
                data1[:-1] = data1
            for data2 in data1[:-1]:
                data = data2.split(" ")
                category = data[0]
                
                # 记录第一个类别的ID
                if self.first_category_id is None:
                    self.first_category_id = category

                # 确保类别使用相同的颜色
                if category not in category_color_map:
                    category_color_map[category] = color_list[len(category_color_map) % len(color_list)]
                color = category_color_map[category]
                center_X = int(float(data[1]) * picWidth*self.scale_factor)
                center_Y = int(float(data[2]) * picHeight*self.scale_factor)
                width = int(float(data[3]) * picWidth*self.scale_factor)
                height = int(float(data[4]) * picHeight*self.scale_factor)
                
#                 print(center_X,center_Y,width,height)

                # 将坐标转换为 Canvas 上的坐标
                canvas_x0 = x_offset + center_X - width / 2
                canvas_y0 = y_offset + center_Y - height / 2
                canvas_x1 = x_offset + center_X + width / 2
                canvas_y1 = y_offset + center_Y + height / 2
                if label_type == "bbox":
                    # 绘制矩形框
                    rectangle_id=self.canvas.create_rectangle(
                        canvas_x0, canvas_y0,
                        canvas_x1, canvas_y1,
                        outline='#%02x%02x%02x' % color, width=2,tags=str(category)+"@"+str(index)+"_"
                    )
                    text_id = self.canvas.create_text(
                        canvas_x0, canvas_y0- 10,
                        text=str(category)+"@"+str(index), fill='red', tags=str(category)+"@"+str(index)+"_"
                    )
                    self.text2rect[text_id]=rectangle_id
                    self.rect2text[rectangle_id] = text_id
                    
                elif label_type == "kpt":
                    # 绘制矩形框和关键点
                    # 绘制矩形框
                    rectangle_id=self.canvas.create_rectangle(
                        canvas_x0, canvas_y0,
                        canvas_x1, canvas_y1,
                        outline='#%02x%02x%02x' % color, width=2,tags=str(category)+"@"+str(index)+"_"
                    )
                    text_id = self.canvas.create_text(
                        canvas_x0, canvas_y0- 10,
                        text=str(category)+"@"+str(index), fill='red', tags=str(category)+"@"+str(index)+"_"
                    )
                    self.text2rect[text_id]=rectangle_id
                    self.rect2text[rectangle_id] = text_id
                    self.keypoint_count=0
                    flag = 1
                    for i in data[5:]:
                        color = color_list[self.index]
                        if flag % 3 == 1:
                            x = i
                        if flag % 3 == 2:
                            y = i 
                        if flag % 3 == 0:
                            tagname=str(index)+"_"+str(int(flag / 3)-1)
                            if float(i) == 2:
                                point_x = x_offset + float(x) * picWidth *self.scale_factor
                                point_y = y_offset + float(y) * picHeight *self.scale_factor
                                 # Create oval and text with the same tag
                                oval_id = self.canvas.create_oval(
                                    point_x - 2, point_y - 2,
                                    point_x + 2, point_y + 2,
                                    outline='#%02x%02x%02x' % color, fill='#%02x%02x%02x' % color, tags=tagname
                                )
                                text_id = self.canvas.create_text(
                                    point_x, point_y - 10,
                                    text=str(int(flag / 3)-1), fill='red', tags=tagname
                                )
#                                 print(oval_id)
                                # Store ids in dictionary
                                self.text2oval[text_id]=oval_id
                                self.oval2text[oval_id] =text_id
                            self.keypoint_count += 1
                        flag += 1
                elif label_type == "seg":
                    # 处理分割标签
                    seg_points = data[5:]
                    points = [(x_offset + float(seg_points[i]) * picWidth, y_offset + float(seg_points[i + 1]) * picHeight) for i in range(0, len(seg_points), 2)]
                    self.canvas.create_polygon(
                        points, outline='#%02x%02x%02x' % color, fill='', width=2
                    )
                
                #行数计算                 
                index+=1
                self.index+=1
        # 打印或使用记录的数据
#         print(f"第一个类别的ID: {self.first_category_id}")
#         print(f"关键点数量: {self.keypoint_count}")
        self.update_status()
    
    
    def display_image(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # 清空画布
        self.canvas.delete("all")
            
        # 根据缩放因子调整图片大小
        img_width = int(pil_image.width * self.scale_factor)
        img_height = int(pil_image.height * self.scale_factor)
        pil_image = pil_image.resize((img_width, img_height), Image.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=pil_image)

        # 更新画布大小为图片大小
        self.canvas.config(width=img_width+50, height=img_height+50)
        
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()
        # 获取画布和图片的尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
#         print("canvas_width,canvas_height",canvas_width,canvas_height)

        # 计算图片在画布上居中的位置
        x = (canvas_width - img_width) / 2
        y = (canvas_height - img_height) / 2
        
        

        # 在画布上居中显示图片
        self.canvas.create_image(x,y, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk  # Keep a reference to avoid garbage collection
        
    def delete_image(self, event=None):
        if self.current_index < 0 or self.current_index >= len(self.image_files):
            return
                          
        imagename = self.image_files[self.current_index]
        new_image_path = os.path.join(self.newimagespath, imagename)
        new_label_path = os.path.join(self.newlabelspath, f"{os.path.splitext(imagename)[0]}.txt")
        
        if os.path.exists(new_image_path):
            os.remove(new_image_path)
        if os.path.exists(new_label_path):
            os.remove(new_label_path)
        self.auto_close_messagebox("图像和标签已在新文件夹删除")
        
    def save_canvas_to_yolo(self, event=None):
        if self.current_index < 0 or self.current_index >= len(self.image_files):
            return

        imagename = self.image_files[self.current_index]
        new_label_path = os.path.join(self.newlabelspath, f"{os.path.splitext(imagename)[0]}.txt")

        # 获取图像尺寸
        image_path = os.path.join(self.imagespath, imagename)
        picture = cv2.imread(image_path)
        if picture is None:
            print(f"Failed to load image: {image_path}")
            return
        picWidth = picture.shape[1]
        picHeight = picture.shape[0]
        
        
        # 确保 Canvas 大小已更新
        self.canvas.update_idletasks()
        # 获取 Canvas 尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        # 计算 Canvas 中图像的偏移量
        img_x_offset = (canvas_width - picWidth * self.scale_factor) / 2
        img_y_offset = (canvas_height - picHeight * self.scale_factor) / 2

        # 收集 Canvas 上所有的对象
        objects = self.canvas.find_all()
        label_type = self.label_type_var.get()

        countRect = 0
        Rect = {}
        category = {}
        for obj_id in objects:
            if self.canvas.type(obj_id) == "rectangle":
                countRect += 1

        for i in range(countRect):
            Rect[i] = set()
            for obj_id in objects:
                tags = self.canvas.gettags(obj_id)
                for tag in tags:
                    if str(i) + "_" in tag:
                        Rect[i].add(obj_id)
                    if "@" + str(i) + "_" in tag:
                        category[i] = tag.split("@")[0]

        if label_type == "bbox":
            yolo_data = ""
            for i in range(countRect):
                rectstr = {}
                for obj_id in Rect[i]:
                    obj_type = self.canvas.type(obj_id)
                    coords = self.canvas.coords(obj_id)
                    if obj_type == "rectangle":
                        x0, y0, x1, y1 = coords

                        # 修正坐标，考虑缩放和偏移量
                        x0_img = (x0 - img_x_offset) / self.scale_factor
                        y0_img = (y0 - img_y_offset) / self.scale_factor
                        x1_img = (x1 - img_x_offset) / self.scale_factor
                        y1_img = (y1 - img_y_offset) / self.scale_factor

                        # 计算中心和尺寸
                        center_X = (x0_img + x1_img) / 2
                        center_Y = (y0_img + y1_img) / 2
                        width = abs(x1_img - x0_img)
                        height = abs(y1_img - y0_img)
                        
                         # 确保坐标在图像范围内
                        x_center = max(0, min(center_X, picWidth))
                        y_center = max(0, min(center_Y, picHeight))

                        # 转换为 YOLO 格式并保留 6 位小数
                        x_center = center_X / picWidth
                        y_center = center_Y / picHeight
                        width = width / picWidth
                        height = height / picHeight

                        # 格式化为 6 位小数
                        x_center_str = f"{x_center:.6f}"
                        y_center_str = f"{y_center:.6f}"
                        width_str = f"{width:.6f}"
                        height_str = f"{height:.6f}"

                        rectstr[i] = f"{category[i]} {x_center_str} {y_center_str} {width_str} {height_str}\n"
                yolo_data += rectstr[i]
            self.mkdir(self.newlabelspath)  # 确保 newlabels 文件夹存在
            with open(new_label_path, "w", encoding="utf-8") as f:
                f.write(yolo_data)

        elif label_type == "kpt":
            yolo_data = ""
            for i in range(countRect):
                line_data = ""
                rectstr = {}
                kptstr = ""
                kpt_points = [None] * self.keypoint_count
                for obj_id in Rect[i]:
                    obj_type = self.canvas.type(obj_id)
                    coords = self.canvas.coords(obj_id)
                    if obj_type == "rectangle":
                        x0, y0, x1, y1 = coords

                        # 修正坐标，考虑缩放和偏移量
                        x0_img = (x0 - img_x_offset) / self.scale_factor
                        y0_img = (y0 - img_y_offset) / self.scale_factor
                        x1_img = (x1 - img_x_offset) / self.scale_factor
                        y1_img = (y1 - img_y_offset) / self.scale_factor

                        # 计算中心和尺寸
                        center_X = (x0_img + x1_img) / 2
                        center_Y = (y0_img + y1_img) / 2
                        width = abs(x1_img - x0_img)
                        height = abs(y1_img - y0_img)
                        
                        
                        # 确保坐标在图像范围内
                        x_center = max(0, min(center_X, picWidth))
                        y_center = max(0, min(center_Y, picHeight))
                        # 转换为 YOLO 格式并保留 6 位小数
                        x_center = center_X / picWidth
                        y_center = center_Y / picHeight
                        width = width / picWidth
                        height = height / picHeight

                        x_center_str = f"{x_center:.6f}"
                        y_center_str = f"{y_center:.6f}"
                        width_str = f"{width:.6f}"
                        height_str = f"{height:.6f}"

                        rectstr[i] = f"{category[i]} {x_center_str} {y_center_str} {width_str} {height_str}"

                    elif obj_type == "oval":
                        x0, y0, x1, y1 = coords

                        # 修正坐标，考虑缩放和偏移量
                        center_X = (x0 + x1) / 2 - img_x_offset
                        center_Y = (y0 + y1) / 2 - img_y_offset
                        
                        
                         # 确保坐标在图像范围内
                        x_center = max(0, min(center_X, picWidth))
                        y_center = max(0, min(center_Y, picHeight))
                        
                        x_center = center_X / picWidth / self.scale_factor
                        y_center = center_Y / picHeight / self.scale_factor
                        visible = "2.000000"

                        x_center_str = f"{x_center:.6f}"
                        y_center_str = f"{y_center:.6f}"

                        tags = self.canvas.gettags(obj_id)
                        for tag in tags:
                            if str(i) + "_" in tag:
                                kpt_points[int(tag.split("_")[1])] = f"{x_center_str} {y_center_str} {visible}"
#                 print(kpt_points)
                for point in kpt_points:
                    if point is None:
                        kptstr += " 0.000000 0.000000 0.000000"
                    else:
                        kptstr += " " + point

                line_data = rectstr[i] + kptstr
                yolo_data += line_data + "\n"
            self.mkdir(self.newlabelspath)  # 确保 newlabels 文件夹存在
            with open(new_label_path, "w", encoding="utf-8") as f:
                f.write(yolo_data)

    def update_status(self):
        self.status_label.config(text=f"第 {self.current_index + 1} 张 / 共 {len(self.image_files)} 张")

    
    
    def on_canvas_click(self, event):
        
        if self.is_modifying:
            # Clear previous selection
            self.canvas.dtag("selected")
            self.start_x=event.x
            self.start_y=event.y
            # Define selection radius
            select_radius = 12

            # Get all items on the canvas
            selected_items = []
#             # 调试
#             all_items = self.canvas.find_all()
#             for item_id in all_items:
#                 item_type = self.canvas.type(item_id)
#                 coords = self.canvas.coords(item_id)
#                 tags = self.canvas.gettags(item_id)
#                 print("id:",item_id,"type:",item_type,"tags:",tags)

            if  self.canvas.find_withtag("current"):
                current_id=self.canvas.find_withtag("current")[0]
                current_tag = self.canvas.gettags(current_id)
                print("on_canvas_click现在点击：",current_id,"tags:",current_tag)
                
                if not self.current_rect:
#                     print(self.current_rect)
                    if self.canvas.type(current_id)=="rectangle":
#                         print("rectangle")
                        self.current_rect=current_id
                        self.create_handles()
#                       print(self.handles)

                    elif self.canvas.type(current_id)=="oval":
                        text_id=self.oval2text[current_id]
                        selected_items.append(current_id)
                        selected_items.append(text_id)
                    
                    elif self.canvas.type(current_id)=="text":
                        if current_id in self.text2oval:
                            oval_id=self.text2oval[current_id]
                            selected_items.append(current_id)
                            selected_items.append(oval_id)
                            
                        if current_id in self.text2rect:
                            rectangle_id=self.text2rect[current_id]
                            selected_items.append(current_id)
                            selected_items.append(rectangle_id)

                        
                else:
                    print("矩形模式")
                    
                    if self.canvas.type(current_id)=="rectangle":   
                        text_id=self.rect2text[current_id]
                        selected_items.append(current_id)
                        selected_items.append(text_id)
                            
                    if self.canvas.type(current_id)=="text":
                        if current_id in self.text2rect:
                            rectangle_id=self.text2rect[current_id]
                            selected_items.append(current_id)
                            selected_items.append(rectangle_id)
                    
#                     if selected_items:
#                         print(selected_items)
#                         # Tag all selected items
#                         for item_id in selected_items:
#                              #print(item_id)
#                             self.canvas.addtag_withtag("selected", item_id)
# #                             if self.canvas.type(item_id)=="text":
#                             self.canvas.tag_bind("selected", '<Double-1>', self.on_double_left_click)
    
            if selected_items:
                print(selected_items)
                # Tag all selected items
                for item_id in selected_items:
                     #print(item_id)
#                     if self.canvas.type(item_id)=="text":
#                         self.canvas.addtag_withtag("selected", item_id)
#                         self.canvas.tag_bind("selected", '<Double-1>', self.on_double_left_click)
                    if not self.canvas.type(item_id)=="rectangle":
                        self.canvas.addtag_withtag("selected", item_id)
                        self.canvas.tag_bind("selected", '<Double-1>', self.on_double_left_click)
                        self.canvas.tag_bind("selected", '<Button1-Motion>', self.on_mouse_drag)
                        self.canvas.tag_bind("selected", '<Button1-ButtonRelease>', self.on_mouse_release)
                    
#                     调试部分
                all_items = self.canvas.find_all()
                for item_id in all_items:
                    item_type = self.canvas.type(item_id)
                    coords = self.canvas.coords(item_id)
                    tags = self.canvas.gettags(item_id)
                    print("id:",item_id,"type:",item_type,"tags:",tags)


        elif self.is_inserting:
           # Add a new keypoint (oval) at the click position
            self.add_keypoint(event.x, event.y)
            
        elif self.is_insertingRect:
            self.start_x=event.x
            self.start_y=event.y
            self.add_rectangle(event)
 
        elif self.is_deleting:
            self.is_modifying=False
            # 删除
            self.canvas.dtag("selected")
            self.start_x=event.x
            self.start_y=event.y
            # Define selection radius
            select_radius = 12

            # Get all items on the canvas
            selected_items = []
            all_items = self.canvas.find_all()
            for item_id in all_items:
                item_type = self.canvas.type(item_id)
                coords = self.canvas.coords(item_id)
                tags = self.canvas.gettags(item_id)
#                 print("id:",item_id,"type:",item_type,"tags:",tags)

            if  self.canvas.find_withtag("current"):
                current_id=self.canvas.find_withtag("current")[0]
                current_tag = self.canvas.gettags(current_id)
#                 print("现在点击：",current_id,"tags:",current_tag)

                if self.canvas.type(current_id)=="text":
                    oval_id=self.text2oval[current_id]
                    selected_items.append(current_id)
                    selected_items.append(oval_id)
                if self.canvas.type(current_id)=="oval":   
                    text_id=self.oval2text[current_id]
                    selected_items.append(current_id)
                    selected_items.append(text_id)

                elif self.canvas.type(current_id) == "rectangle":
                    text_id=self.rect2text[current_id]
                    self.canvas.delete(current_id)
                    self.canvas.delete(text_id)

                if selected_items:
#                     print(selected_items)
                    # Tag all selected items
                    for item_id in selected_items:
        #                 print(item_id)
                        self.canvas.addtag_withtag("selected", item_id)
            self.delete_selected(event)
    
    #增加    
    def add_keypoint(self, x, y):
        self.is_changed=True
        # Check if an oval with the same tag already exists
        all=self.canvas.find_all()
        alltags={}
        for i in range(self.index):
            alltags[i]=set()
            for item in all:
                tags=self.canvas.gettags(item)
                for tag in tags:
                    if str(i)+"_" in tag and not tag.endswith('_'):
                        alltags[i].add(tag)
#         print(alltags)

        available_tag = self.find_available_tag(alltags)

        if available_tag is not None:
            # Create a new oval at the specified position with the available tag
            point_x = x
            point_y = y
            
            oval_id = self.canvas.create_oval(
                point_x - 2, point_y - 2,
                point_x + 2, point_y + 2,
                outline='cyan', fill='cyan', tags=available_tag
            )
            text_id = self.canvas.create_text(
                point_x, point_y - 10,
                text=available_tag.split("_")[1], fill='red', tags=available_tag
            )
            # Store IDs in dictionary
            self.text2oval[text_id] = oval_id
            self.oval2text[oval_id] = text_id
            self.keypoint_count += 1
        else:
            self.auto_close_messagebox("关键点都已存在，无法再新建，请检查！")
            
    def add_rectangle(self,event):
        self.is_changed=True
        if self.start_x and self.start_y and self.is_insertingRect:
            # 绘制矩形框
            rectangle_id=self.canvas.create_rectangle(
                event.x-100, event.y-100,
                event.x+100, event.y+100,
                outline='green', width=2,tags="@"+str(self.index)+"_"
            )
            text_id = self.canvas.create_text(
                event.x, event.y- 10,
                text="@"+str(self.index)+"_", fill='red', tags="@"+str(self.index)+"_"
            )
            self.text2rect[text_id]=rectangle_id
            self.rect2text[rectangle_id] = text_id
            
    #删除        
    def delete_selected(self, event):
        self.is_changed=True
        if self.is_deleting:
            # Get all items with the 'selected' tag
            selected_items = self.canvas.find_withtag("selected")
            current_rect=self.current_rect
    #         print("ssssssssssssssssssssssssssssssssss")
            for item_id in selected_items:
                item_type = self.canvas.type(item_id)
                if item_type == "oval":
                    # Find the associated text
                    text_id = self.oval2text.get(item_id)
                    if text_id:
                        # Delete the text item
                        self.canvas.delete(text_id)
                        # Remove the mapping
                        del self.oval2text[item_id]
                        del self.text2oval[text_id]

                    # Delete the oval item
                    self.canvas.delete(item_id)

                elif item_type == "text":
                    # Find the associated oval
                    oval_id = self.text2oval.get(item_id)
                    if oval_id:
                        # Delete the oval item
                        self.canvas.delete(oval_id)
                        # Remove the mapping
                        del self.oval2text[oval_id]
                        del self.text2oval[item_id]

                    # Delete the text item
                    self.canvas.delete(item_id)

            # Optionally, clear the selection tag after deletion
            self.canvas.dtag("selected")          
            


    #修改        
    def on_double_left_click(self, event):
        self.is_changed=True
        if not self.is_dragging:
            #找所有
            all=self.canvas.find_all()
            alltags={}
            for i in range(self.index):
                alltags[i]=set()
                for item in all:
                    tags=self.canvas.gettags(item)
                    for tag in tags:
                        if str(i)+"_" in tag :
                            alltags[i].add(tag)

#             print("sssssssssssssssss",alltags)
            # Find the tag of the currently selected item
            items = self.canvas.find_withtag('selected')
            for item_id in items:
                item_type = self.canvas.type(item_id)
                if item_type == "text":
                    if item_id in self.text2oval:
                        oval_id=self.text2oval[item_id]
                        tags=self.canvas.gettags(oval_id)
                        for tag in tags:
                            if "_" in tag and not tag.endswith("_"):
                                current_text = self.canvas.itemcget(item_id, 'text')
                                new_text = askstring("Edit Text", "Enter new text:", initialvalue=tag.split("_")[0]+"_"+current_text)
                                for i in range(self.keypoint_count):
                                    for j in range(self.index):
                                        if new_text in alltags[j]:
                                            new_text=None
                                        
                                if new_text:
                                    if '_' in new_text:
                                     # 更新 Canvas 上的文本
                                        if new_text !=tag.split("_")[0]+"_"+current_text:
                                            self.canvas.itemconfig(item_id, text=new_text.split("_")[1])
                                            self.canvas.addtag_withtag(new_text, item_id)
                                            self.canvas.addtag_withtag(new_text, oval_id)
                                            # 修改 oval 的颜色（例如设置为红色）
                                            color = self.color_list[int(new_text.split("_")[0])]
                                            self.canvas.itemconfig(oval_id,outline='#%02x%02x%02x' % color, fill='#%02x%02x%02x' % color)
                                            self.canvas.dtag(oval_id, tag.split("_")[0]+"_"+current_text)
                                            self.canvas.dtag(item_id, tag.split("_")[0]+"_"+current_text)
                                    else:
                                        self.auto_close_messagebox("请按照"+"数量_关键点序号"+"格式来")
                                else:
                                    self.auto_close_messagebox("名称已存在或关键点已存在")
                                                    
                if item_id in self.text2rect:   
                    rectangle_id=self.text2rect[item_id]
                    tags=self.canvas.gettags(rectangle_id)
                    for tag in tags:
                        if "_" in tag and tag.endswith("_"):
#                             print("sssssssssssssssssssssssssssssss1111ssss")
#                             print(tag)
                            current_text = self.canvas.itemcget(item_id, 'text')
                            new_text = askstring("Edit Text", "Enter new text:", initialvalue=tag.split("_")[0]+"_")
                            for j in range(self.index): 
#                                 print("ssssss")
                                if new_text in alltags[j]:
                                    new_text=None
#                                     print(tag)
#                                     print("new_text",new_text)
#                                     print("current text",current_text)
                            if new_text:
                                if '_' in new_text and '@' in new_text :
                                 # 更新 Canvas 上的文本

                                    if new_text.split("_")[0]!=current_text:
                                        self.canvas.itemconfig(item_id, text=new_text.split("_")[0])
                                        self.canvas.addtag_withtag(new_text, item_id)
                                        self.canvas.addtag_withtag(new_text, rectangle_id)
                                        self.canvas.dtag(rectangle_id, tag.split("_")[0]+"_")
                                        self.canvas.dtag(item_id, tag.split("_")[0]+"_")
                                else:
                                    self.auto_close_messagebox("请按照"+"类别@数量_"+"格式来")
#                                     print("报错按照格式来")
                            else:
                                self.auto_close_messagebox("名称已存在")
                                            

        
    def create_handles(self):
        """创建矩形的手柄"""
        if self.current_rect:
            # 清除已有手柄
            for handle in self.handles:
                self.canvas.delete(handle)
            self.handles = []

            # 获取矩形的坐标
            coords = self.canvas.coords(self.current_rect)
            x0, y0, x1, y1 = coords

            # 创建手柄
            self.handles.append(self.canvas.create_oval(x0 - 5, y0 - 5, x0 + 5, y0 + 5, fill='red', tags='handle'))
            self.handles.append(self.canvas.create_oval(x1 - 5, y0 - 5, x1 + 5, y0 + 5, fill='red', tags='handle'))
            self.handles.append(self.canvas.create_oval(x0 - 5, y1 - 5, x0 + 5, y1 + 5, fill='red', tags='handle'))
            self.handles.append(self.canvas.create_oval(x1 - 5, y1 - 5, x1 + 5, y1 + 5, fill='red', tags='handle'))

            # 绑定手柄的事件
            for handle in self.handles:
                self.canvas.tag_bind(handle, '<ButtonPress-1>', self.on_handle_press)
                self.canvas.tag_bind(handle, '<B1-Motion>', self.on_handle_drag)
                self.canvas.tag_bind(handle, '<ButtonRelease-1>', self.on_handle_release)
                
    def update_handles(self):
        """更新手柄的位置"""
        if self.current_rect:
            coords = self.canvas.coords(self.current_rect)
            x0, y0, x1, y1 = coords

            # 更新手柄的位置
            self.canvas.coords(self.handles[0], x0 - 5, y0 - 5, x0 + 5, y0 + 5)
            self.canvas.coords(self.handles[1], x1 - 5, y0 - 5, x1 + 5, y0 + 5)
            self.canvas.coords(self.handles[2], x0 - 5, y1 - 5, x0 + 5, y1 + 5)
            self.canvas.coords(self.handles[3], x1 - 5, y1 - 5, x1 + 5, y1 + 5)

            
    def on_handle_press(self, event):
        """手柄按下事件处理函数"""
        self.dragging_handle = self.canvas.find_closest(event.x, event.y, halo=5)[0]
        
    def on_handle_drag(self, event):
        self.is_changed=True
        """手柄拖动事件处理函数"""
        event.x,event.y=self.clip_event_coords_to_image_bounds(event,self.canvas,self.img_width,self.img_height)
        handle_coords = self.canvas.coords(self.dragging_handle)
        handle_x0, handle_y0, handle_x1, handle_y1 = handle_coords
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)
        
        # 调整矩形大小
        self.adjust_rectangle(cur_x, cur_y)

    def on_handle_release(self, event):
        """手柄释放事件处理函数"""
        self.dragging_handle = None
        response = messagebox.askyesno("确认", "您确定要修改完毕？")
        if response:
            self.current_rect = None
            for handle in self.handles:
                self.canvas.delete(handle)
            self.handles = []


    def adjust_rectangle(self, cur_x, cur_y):
        """调整矩形的大小"""
        coords = self.canvas.coords(self.current_rect)
        x0, y0, x1, y1 = coords
        
        if self.dragging_handle in self.handles:
            handle_index = self.handles.index(self.dragging_handle)
            
            if handle_index == 0:  # 左上角手柄
                x0, y0 = cur_x, cur_y
            elif handle_index == 1:  # 右上角手柄
                x1, y0 = cur_x, cur_y
            elif handle_index == 2:  # 左下角手柄
                x0, y1 = cur_x, cur_y
            elif handle_index == 3:  # 右下角手柄
                x1, y1 = cur_x, cur_y
            
            # 更新矩形的坐标
            self.canvas.coords(self.current_rect, x0, y0, x1, y1)
            # 更新手柄的位置
            self.update_handles()
            #更新标签位置
            text_id=self.rect2text[self.current_rect]
            self.canvas.coords(text_id, x0,y0-10)

    def on_mouse_drag(self, event):
        self.is_changed=True
        if self.start_x is None or self.start_y is None:
            return
#         print(self)
        self.is_dragging=True
        event.x,event.y=self.clip_event_coords_to_image_bounds(event,self.canvas,self.img_width,self.img_height)
        dx = event.x - self.start_x
        dy = event.y - self.start_y

        # Find the tag of the currently selected item
        items = self.canvas.find_withtag('selected')
#         print(items)
        for item_id in items:
            if not self.canvas.type(item_id)=="rectangle":
                if item_id not in self.data:
                    self.data[item_id] = {'coords': self.canvas.coords(item_id)}
                self.canvas.move(item_id, dx, dy)

        # Update the start coordinates
        self.start_x = event.x
        self.start_y = event.y
    
    def on_mouse_release(self, event):
        if self.is_dragging:
            # Ask for confirmation
            response = messagebox.askyesno("Confirm Move", "Do you want to confirm the move?")
            if response:
                # Confirm the move, do nothing additional
#                 print("Move confirmed")
                pass
            else:
                # Undo the move, restore original positions
                self.undo_move()
#                 print("Move canceled")
            # Clear selection after operation
            self.canvas.dtag("selected")
            self.selected_items = []
            self.start_x = None
            self.start_y = None
        self.is_dragging=False

    def undo_move(self):
        items = self.canvas.find_withtag('selected')
#         print(items)
        for item_id in items:
        # Restore the positions of the moved items
            coords = self.canvas.coords(item_id)
            original_coords = self.data.get(item_id, {'coords': coords})
            self.canvas.coords(item_id, *original_coords['coords'])
        self.data={}



# 创建并运行应用
root = tk.Tk()
app = ImageLabeler(root)
app.show_instructions()
root.mainloop()
