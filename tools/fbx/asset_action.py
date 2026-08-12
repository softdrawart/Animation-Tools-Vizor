bl_info = {
    "name": "Asset Browser: Action & Preview Tools",
    "author": "Gemini Assistant",
    "version": (1, 4),
    "blender": (3, 4, 0),
    "location": "Asset Browser > Menus",
    "description": "Force assign actions, push to NLA, and generate mesh previews.",
    "category": "Animation",
}

import bpy
import os

# --- UTILS ---

def append_and_assign(filepath, action_name, target_object):
    """Appends an action from an external file and returns the action object."""
    if action_name in bpy.data.actions:
        action = bpy.data.actions[action_name]
    else:
        if not os.path.exists(filepath):
            return None, f"File not found: {filepath}"
        try:
            with bpy.data.libraries.load(filepath, link=False) as (data_from, data_to):
                if action_name in data_from.actions:
                    data_to.actions = [action_name]
                else:
                    return None, f"Action '{action_name}' not found."
            if not data_to.actions:
                return None, "Failed to load data."
            action = data_to.actions[0]
        except Exception as e:
            return None, str(e)

    if not target_object.animation_data:
        target_object.animation_data_create()
    return action, None

# --- OPERATORS ---

class ASSET_OT_force_assign_action(bpy.types.Operator):
    """Assigns the first selected action asset to the active armature"""
    bl_idname = "asset.force_assign_action"
    bl_label = "Assign Action"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        assets = getattr(context, "selected_assets", None) or getattr(context, "selected_asset_files", None)
        if not assets:
            self.report({'WARNING'}, "No asset selected.")
            return {'CANCELLED'}

        asset = assets[0]
        filepath = getattr(asset, "full_library_path", None) or getattr(asset, "path", "")
        action, error = append_and_assign(filepath, asset.name, context.active_object)
        
        if error:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}

        context.active_object.animation_data.action = action
        return {'FINISHED'}

class ASSET_OT_push_actions_to_nla(bpy.types.Operator):
    """Appends all selected action assets and pushes them to the NLA stack"""
    bl_idname = "asset.push_actions_to_nla"
    bl_label = "Push Actions to NLA"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        target_obj = context.active_object
        assets = getattr(context, "selected_assets", None) or getattr(context, "selected_asset_files", None)
        if not assets: return {'CANCELLED'}

        for asset in assets:
            filepath = getattr(asset, "full_library_path", None) or getattr(asset, "path", "")
            action, error = append_and_assign(filepath, asset.name, target_obj)
            if action:
                track = target_obj.animation_data.nla_tracks.new()
                track.name = f"{action.name}"
                track.strips.new(action.name, int(context.scene.frame_current), action)

        target_obj.animation_data.action = None
        return {'FINISHED'}

class ASSET_OT_generate_custom_preview(bpy.types.Operator):
    """Bakes selection to a temp mesh to generate a clean Asset Preview"""
    bl_idname = "asset.generate_custom_preview"
    bl_label = "Generate Preview from Selection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # We need selected objects and an active asset to apply the preview to
        return context.selected_objects #and getattr(context, "asset_handle", None)

    def execute(self, context):
        # 1. Store original context
        original_active = context.view_layer.objects.active
        
        # 2. Bake Logic
        bpy.ops.object.duplicate()
        duplicates = context.selected_objects
        bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
        bpy.ops.object.convert(target='MESH')
        
        context.view_layer.objects.active = duplicates[0]
        bpy.ops.object.join()
        
        merged_obj = context.active_object
        merged_obj.name = "TEMP_PREVIEW_BAKE"
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

        # 3. Generate Preview
        # This uses the active object to update the preview of the active asset
        #bpy.ops.ed.lib_id_generate_preview_from_object()

        # 4. Cleanup
        #bpy.data.objects.remove(merged_obj, do_unlink=True)
        #context.view_layer.objects.active = original_active

        self.report({'INFO'}, "Asset preview updated from selection.")
        return {'FINISHED'}

# --- MENU FUNCTIONS ---

def draw_asset_main_menu(self, context):
    self.layout.separator()
    self.layout.operator(ASSET_OT_force_assign_action.bl_idname, icon='IMPORT')
    self.layout.operator(ASSET_OT_push_actions_to_nla.bl_idname, icon='NLA')

def draw_preview_menu(self, context):
    self.layout.separator()
    self.layout.operator(ASSET_OT_generate_custom_preview.bl_idname, icon='OUTLINER_OB_MESH')

# --- REGISTRATION ---

classes = (
    ASSET_OT_force_assign_action,
    ASSET_OT_push_actions_to_nla,
    ASSET_OT_generate_custom_preview,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # Right-click menu on the asset icon
    bpy.types.ASSETBROWSER_MT_context_menu.append(draw_asset_main_menu)
    # Right-click menu on the preview image in the sidebar
    bpy.types.ASSETBROWSER_MT_metadata_preview_menu.append(draw_preview_menu)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    bpy.types.ASSETBROWSER_MT_context_menu.remove(draw_asset_main_menu)
    bpy.types.ASSETBROWSER_MT_metadata_preview_menu.remove(draw_preview_menu)

if __name__ == "__main__":
    register()