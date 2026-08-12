

import bpy
from mathutils import Matrix

# --- CORE LOGIC ---

def run_cursor_update(scene):
    props = scene.cursor_tracker_props
    if not props.is_active or not props.target_object:
        return

    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        obj = props.target_object
        eval_obj = obj.evaluated_get(depsgraph)
        
        target_matrix = Matrix.Identity(4)

        if obj.type == 'ARMATURE' and props.bone_name and props.bone_name in eval_obj.pose.bones:
            bone = eval_obj.pose.bones[props.bone_name]
            target_matrix = eval_obj.matrix_world @ bone.matrix
        else:
            target_matrix = eval_obj.matrix_world

        scene.cursor.location = target_matrix.to_translation()
        
        if scene.cursor.rotation_mode != 'XYZ':
            scene.cursor.rotation_mode = 'XYZ'
        scene.cursor.rotation_euler = target_matrix.to_euler()
        
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
    except Exception:
        pass

# --- HANDLERS ---

@bpy.app.handlers.persistent
def on_frame_change(scene):
    run_cursor_update(scene)

@bpy.app.handlers.persistent
def on_depsgraph_update(scene, depsgraph):
    run_cursor_update(scene)

# --- PROPERTIES ---

class CursorTrackerProperties(bpy.types.PropertyGroup):
    is_active: bpy.props.BoolProperty(
        name="Track Target",
        default=False
    )
    target_object: bpy.props.PointerProperty(
        name="Target",
        type=bpy.types.Object
    )
    bone_name: bpy.props.StringProperty(
        name="Bone"
    )

# --- OPERATORS ---

class CURSOR_OT_pick_object(bpy.types.Operator):
    """Set the target to the currently active object"""
    bl_idname = "cursor.pick_active_object"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        if context.active_object:
            context.scene.cursor_tracker_props.target_object = context.active_object
        return {'FINISHED'}

class CURSOR_OT_pick_bone(bpy.types.Operator):
    """Set the bone to the currently active pose bone"""
    bl_idname = "cursor.pick_active_bone"
    bl_label = ""
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cursor_tracker_props
        obj = context.active_object
        bone = context.active_pose_bone
        
        if obj and obj.type == 'ARMATURE' and bone:
            props.target_object = obj
            props.bone_name = bone.name
        elif bone:
            props.bone_name = bone.name
            
        return {'FINISHED'}

# --- UI PANEL ---

class VIEW3D_PT_cursor_tracker(bpy.types.Panel):
    bl_label = "3D Cursor Tracker"
    bl_idname = "VIEW3D_PT_cursor_tracker"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        props = context.scene.cursor_tracker_props

        # Object Row
        row = layout.row(align=True)
        row.prop(props, "target_object")
        row.operator("cursor.pick_active_object", icon='EYEDROPPER')
        
        # Bone Row (Only shows if target is armature)
        if props.target_object and props.target_object.type == 'ARMATURE':
            row = layout.row(align=True)
            row.prop_search(props, "bone_name", props.target_object.pose, "bones", text="Bone", icon='BONE_DATA')
            row.operator("cursor.pick_active_bone", icon='EYEDROPPER')

        layout.separator()
        
        icon = 'PLAY' if not props.is_active else 'PAUSE'
        text = "Activate Tracking" if not props.is_active else "Deactivate Tracking"
        layout.prop(props, "is_active", text=text, toggle=True, icon=icon)

# --- REGISTRATION ---

classes = (
    CursorTrackerProperties,
    CURSOR_OT_pick_object,
    CURSOR_OT_pick_bone,
    VIEW3D_PT_cursor_tracker,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.cursor_tracker_props = bpy.props.PointerProperty(type=CursorTrackerProperties)

    if on_frame_change not in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.append(on_frame_change)
    if on_depsgraph_update not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(on_depsgraph_update)

def unregister():
    if on_frame_change in bpy.app.handlers.frame_change_post:
        bpy.app.handlers.frame_change_post.remove(on_frame_change)
    if on_depsgraph_update in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(on_depsgraph_update)

    del bpy.types.Scene.cursor_tracker_props

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()