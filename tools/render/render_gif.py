import bpy
import os
import sys
import subprocess
import urllib.request
import zipfile
import shutil
from bpy.props import StringProperty
from bpy.types import Operator, Panel

# ------------------------------------------------------------------------
#   Helper: Get Local FFmpeg Path
# ------------------------------------------------------------------------

def get_ffmpeg_path():
    """Returns the path to the bundled ffmpeg.exe inside this addon's folder."""
    # Gets the directory where this specific .py file lives
    addon_dir = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(addon_dir, "bin", "ffmpeg.exe")

# ------------------------------------------------------------------------
#   Operator: Auto-Download FFmpeg (Windows)
# ------------------------------------------------------------------------

class GIF_OT_download_ffmpeg(Operator):
    """Downloads and extracts a lightweight static build of FFmpeg to the addon folder"""
    bl_idname = "gif.download_ffmpeg"
    bl_label = "Download FFmpeg Dependencies"
    
    def execute(self, context):
        if not sys.platform.startswith("win"):
            self.report({'ERROR'}, "Auto-download currently only supports Windows.")
            return {'CANCELLED'}

        # Reliable, automated Windows build URL
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        
        addon_dir = os.path.dirname(os.path.realpath(__file__))
        bin_dir = os.path.join(addon_dir, "bin")
        temp_zip = os.path.join(addon_dir, "ffmpeg_temp.zip")
        
        # Create bin folder if it doesn't exist
        if not os.path.exists(bin_dir):
            os.makedirs(bin_dir)
            
        try:
            print("Starting FFmpeg download...")
            self.report({'INFO'}, "Downloading FFmpeg... Blender will pause for a few seconds.")
            
            # Download the zip file
            urllib.request.urlretrieve(url, temp_zip)
            
            # Extract ONLY the ffmpeg.exe file (ignores the zip's internal folder structure)
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                for file_name in zip_ref.namelist():
                    if file_name.endswith("ffmpeg.exe"):
                        # Read the raw bytes and copy them directly to our target path
                        source = zip_ref.open(file_name)
                        target = open(os.path.join(bin_dir, "ffmpeg.exe"), "wb")
                        with source, target:
                            shutil.copyfileobj(source, target)
                        break
                        
            # Clean up the downloaded zip file
            os.remove(temp_zip)
            self.report({'INFO'}, "FFmpeg successfully installed into add-on!")
            print("FFmpeg installation complete.")
            
        except Exception as e:
            self.report({'ERROR'}, f"Failed to download FFmpeg: {e}")
            if os.path.exists(temp_zip):
                os.remove(temp_zip)
            return {'CANCELLED'}
            
        return {'FINISHED'}

# ------------------------------------------------------------------------
#   Operator: Convert Existing PNGs to GIF
# ------------------------------------------------------------------------

class GIF_OT_convert(Operator):
    """Converts rendered PNG sequence to GIF using FFmpeg"""
    bl_idname = "gif.convert"
    bl_label = "Convert to GIF"

    def execute(self, context):
        scene = context.scene
        ffmpeg_exe = get_ffmpeg_path()

        if not os.path.exists(ffmpeg_exe):
            self.report({'ERROR'}, "FFmpeg dependency is missing.")
            return {'CANCELLED'}

        filepath = scene.render.filepath
        abs_filepath = bpy.path.abspath(filepath)
        render_dir = os.path.dirname(abs_filepath)
        filename_prefix = os.path.basename(abs_filepath)
        
        if not render_dir:
            render_dir = bpy.path.abspath("//")
            
        try:
            files = [f for f in os.listdir(render_dir) if f.endswith('.png')]
        except FileNotFoundError:
             self.report({'ERROR'}, "Render directory does not exist.")
             return {'CANCELLED'}

        if not files:
            self.report({'ERROR'}, "Error: No PNGs rendered at location")
            return {'CANCELLED'}

        gifs_dir = os.path.join(render_dir, "gifs")
        if not os.path.exists(gifs_dir):
            os.makedirs(gifs_dir)

        clean_path = os.path.normpath(render_dir)
        current_folder_name = os.path.basename(clean_path)
        parent_path = os.path.dirname(clean_path)
        parent_folder_name = os.path.basename(parent_path)
        
        if parent_folder_name and current_folder_name:
            gif_name = f"{parent_folder_name}_{current_folder_name}.gif"
        elif current_folder_name:
            gif_name = f"{current_folder_name}.gif"
        else:
            gif_name = "animation.gif"
            
        output_file = os.path.join(gifs_dir, gif_name)
        input_pattern = os.path.join(render_dir, f"{filename_prefix}%04d.png")
        fps = scene.render.fps

        cmd = [
            ffmpeg_exe,
            '-y',
            '-framerate', str(fps),
            '-i', input_pattern,
            '-filter_complex', "[0:v]palettegen=stats_mode=diff[p];[0:v][p]paletteuse", 
            output_file
        ]
        
        try:
            subprocess.run(cmd, check=True)
            self.report({'INFO'}, "GIF Conversion Finished!")
        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"FFmpeg Error: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}

# ------------------------------------------------------------------------
#   Operator: Render (Modal) then Call Convert
# ------------------------------------------------------------------------

class GIF_OT_render_generate(Operator):
    """Renders animation then converts to GIF"""
    bl_idname = "gif.render_generate"
    bl_label = "Export as GIF"
    
    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if context.scene.gif_is_rendering:
                pass
            else:
                context.window_manager.event_timer_remove(self._timer)
                bpy.app.handlers.render_complete.remove(self.stop_render_flag)
                bpy.app.handlers.render_cancel.remove(self.stop_render_flag)
                
                self.report({'INFO'}, "Render finished. Starting GIF conversion...")
                bpy.ops.gif.convert()
                
                return {'FINISHED'}
        return {'PASS_THROUGH'}

    def execute(self, context):
        context.scene.render.image_settings.file_format = 'PNG'
        context.scene.gif_is_rendering = True

        bpy.app.handlers.render_complete.append(self.stop_render_flag)
        bpy.app.handlers.render_cancel.append(self.stop_render_flag)

        bpy.ops.render.render('INVOKE_DEFAULT', animation=True)

        self._timer = context.window_manager.event_timer_add(1.0, window=context.window)
        context.window_manager.modal_handler_add(self)

        return {'RUNNING_MODAL'}
    
    def stop_render_flag(self, scene, context=None):
        scene.gif_is_rendering = False

# ------------------------------------------------------------------------
#   Operator: Batch Process Folders
# ------------------------------------------------------------------------

class GIF_OT_batch_process(Operator):
    """Recursively search for folders with PNGs and convert them"""
    bl_idname = "gif.batch_process"
    bl_label = "Batch Convert Folder"
    
    directory: StringProperty(
        name="Root Folder",
        description="Select the root folder to search recursively",
        subtype='DIR_PATH'
    )

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        root_folder = self.directory
        scene = context.scene
        original_filepath = scene.render.filepath
        folders_processed = 0

        for dirpath, dirnames, filenames in os.walk(root_folder):
            if "gifs" in dirnames:
                dirnames.remove("gifs")

            pngs = [f for f in filenames if f.lower().endswith('.png')]
            
            if pngs:
                common_prefix = os.path.commonprefix(pngs)
                base_prefix = common_prefix.rstrip('0123456789')
                temp_filepath = os.path.join(dirpath, base_prefix)
                scene.render.filepath = temp_filepath
                
                try:
                    res = bpy.ops.gif.convert('EXEC_DEFAULT')
                    if 'FINISHED' in res:
                        folders_processed += 1
                except Exception:
                    continue

        scene.render.filepath = original_filepath
        
        if folders_processed > 0:
            self.report({'INFO'}, f"Batch Complete. Processed {folders_processed} folders.")
        else:
            self.report({'WARNING'}, "Batch Complete. No PNG sequences found.")

        return {'FINISHED'}

# ------------------------------------------------------------------------
#   UI Panel
# ------------------------------------------------------------------------

class GIF_PT_panel(Panel):
    bl_label = "GIF Export"
    bl_idname = "RENDER_PT_gif_export"

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_context = "Render"

    def draw(self, context):
        layout = self.layout
        ffmpeg_exe = get_ffmpeg_path()

        # Conditionally show UI based on whether FFmpeg exists locally
        if not os.path.exists(ffmpeg_exe):
            layout.alert = True
            layout.label(text="FFmpeg dependency missing", icon='ERROR')
            layout.operator("gif.download_ffmpeg", text="Download FFmpeg (Windows)", icon='IMPORT')
        else:
            layout.operator("gif.render_generate", text="Render & Convert to GIF", icon='RENDER_ANIMATION')
            layout.separator()
            layout.operator("gif.convert", text="Convert Existing to GIF", icon='FILE_MOVIE')
            layout.operator("gif.batch_process", text="Recursive Batch Convert", icon='FILE_FOLDER')

# ------------------------------------------------------------------------
#   Registration
# ------------------------------------------------------------------------

classes = (
    GIF_OT_download_ffmpeg,
    GIF_OT_convert,
    GIF_OT_render_generate,
    GIF_OT_batch_process,
    GIF_PT_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.gif_is_rendering = bpy.props.BoolProperty(default=False)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gif_is_rendering

if __name__ == "__main__":
    register()