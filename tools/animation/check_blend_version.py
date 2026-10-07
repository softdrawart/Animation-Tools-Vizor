import bpy
import os
import shutil
import zstandard as zstd
from datetime import datetime

class BlenderVersionPopup(bpy.types.Operator):
    bl_idname = "wm.blender_version_popup"
    bl_label = "Информация о файле"
    bl_options = {'REGISTER', 'INTERNAL'}
    
    version_msg: bpy.props.StringProperty(default="")
    date_msg: bpy.props.StringProperty(default="")
    
    def execute(self, context):
        return {'FINISHED'}
        
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)
        
    def draw(self, context):
        layout = self.layout
        # Выводим две строки с иконками
        layout.label(text=self.version_msg, icon='INFO')
        layout.label(text=self.date_msg, icon='TIME')

class VIEW3D_PT_file_version_panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'
    bl_label = "Инфо о файле"

    def draw(self, context):
        layout = self.layout
        layout.operator("wm.check_file_version_operator", text="Узнать версию и дату", icon='FILE_BLEND')

class WM_OT_check_file_version_operator(bpy.types.Operator):
    bl_idname = "wm.check_file_version_operator"
    bl_label = "Проверить файл"
    
    def execute(self, context):
        filepath = bpy.data.filepath

        if not filepath:
            self.report({'WARNING'}, "Файл еще не сохранен на диск!")
            bpy.ops.wm.blender_version_popup('INVOKE_DEFAULT', version_msg="Внимание: Файл не сохранен!", date_msg="")
            return {'FINISHED'}

        temp_filepath = filepath + ".temp_version_check"
        version_result = ""
        date_result = ""
        
        try:
            # Получаем дату изменения оригинального файла
            mtime = os.path.getmtime(filepath)
            # Форматируем в привычный вид: ДД.ММ.ГГГГ ЧЧ:ММ:СС
            date_result = f"Изменен: {datetime.fromtimestamp(mtime).strftime('%d.%m.%Y %H:%M:%S')}"
            
            # Копируем файл для чтения версии
            shutil.copy2(filepath, temp_filepath)
            
            with open(temp_filepath, 'rb') as f:
                file_data = f.read(65536)
                
                if file_data.startswith(b'\x28\xB5\x2F\xFD'):
                    dctx = zstd.ZstdDecompressor()
                    file_data = dctx.decompress(file_data, max_output_size=1024)
                
                if b'BLENDER' in file_data:
                    idx = file_data.find(b'BLENDER')
                    ver_bytes = file_data[idx+9:idx+12]
                    version_str = ver_bytes.decode('utf-8', errors='ignore')
                    
                    major = version_str[0]
                    minor = version_str[1:]
                    if minor.startswith('0'):
                        minor = minor[1:]
                    
                    version_result = f"Оригинальная версия файла: {major}.{minor}"
                else:
                    version_result = "Ошибка: Не удалось распознать структуру файла."
                    
        except Exception as e:
            version_result = f"Ошибка скрипта: {e}"
            date_result = "Не удалось определить дату"
            
        finally:
            if os.path.exists(temp_filepath):
                try:
                    os.remove(temp_filepath)
                except:
                    pass

        # Вызываем окно и передаем оба сообщения
        bpy.ops.wm.blender_version_popup('INVOKE_DEFAULT', version_msg=version_result, date_msg=date_result)
        return {'FINISHED'}

classes = (
    BlenderVersionPopup,
    VIEW3D_PT_file_version_panel,
    WM_OT_check_file_version_operator,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()