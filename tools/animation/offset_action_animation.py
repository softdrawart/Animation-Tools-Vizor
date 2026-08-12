
import bpy

def get_mirror_name(name):
    if name.endswith(".L"): return name[:-2] + ".R"
    if name.endswith(".R"): return name[:-2] + ".L"
    if name.endswith("_L"): return name[:-2] + "_R"
    if name.endswith("_R"): return name[:-2] + "_L"
    return None

def mirror_pose_values(source_bone, target_bone):
    """
    Applies the mirrored transform of source_bone to target_bone.
    This mimics Blender's 'Paste X-Flipped' logic.
    """
    # Location: Flip X
    loc = source_bone.location.copy()
    loc.x *= -1
    target_bone.location = loc
    
    # Rotation: Quaternion (W, X remain same, Y, Z flip)
    if source_bone.rotation_mode == 'QUATERNION':
        rot = source_bone.rotation_quaternion.copy()
        rot.y *= -1
        rot.z *= -1
        target_bone.rotation_quaternion = rot
    # Rotation: Euler (X remains same, Y, Z flip)
    else:
        rot = source_bone.rotation_euler.copy()
        rot.y *= -1
        rot.z *= -1
        target_bone.rotation_euler = rot
        
    # Scale: Remains the same
    target_bone.scale = source_bone.scale.copy()

class ANIM_OT_MirrorKeyframesOffset(bpy.types.Operator):
    """Mirror only existing keyframes with a time offset and loop"""
    bl_idname = "anim.mirror_keyframes_offset"
    bl_label = "Mirror Keyframes (Offset)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'ERROR'}, "Active object must have an Animation Action")
            return {'CANCELLED'}

        scene = context.scene
        start = scene.frame_start
        end = scene.frame_end
        # Duration is total frames in the loop (usually end - start for cycling)
        duration = end - start 
        offset = context.window_manager.mirror_anim_offset
        
        selected_bones = context.selected_pose_bones
        original_frame = scene.frame_current

        # 1. Map Source Bones to Target Bones
        bone_pairs = []
        for s_bone in selected_bones:
            m_name = get_mirror_name(s_bone.name)
            if m_name and m_name in obj.pose.bones:
                bone_pairs.append((s_bone, obj.pose.bones[m_name]))

        if not bone_pairs:
            self.report({'ERROR'}, "No mirrored counterparts found for selection")
            return {'CANCELLED'}

        # 2. Process each pair
        for source, target in bone_pairs:
            # Find all unique keyframe times for this specific bone
            keyframes = set()
            data_path_prefix = f'pose.bones["{source.name}"]'
            
            for fcurve in obj.animation_data.action.fcurves:
                if fcurve.data_path.startswith(data_path_prefix):
                    for kp in fcurve.keyframe_points:
                        # Only grab keyframes within current playback range
                        if start <= kp.co.x <= end:
                            keyframes.add(int(kp.co.x))
            
            # 3. Apply Mirrored Pose at each keyframe time
            # We store data first to avoid context switching issues during reading
            mirrored_data = []
            for f in keyframes:
                scene.frame_set(f)
                
                # Logic for Loop Offset
                # (f - start) converts frame to 0-indexed relative to start
                # Adding offset and using modulo duration wraps it
                # Adding start back puts it in the correct scene range
                target_f = ((f - start + offset) % duration) + start
                
                # Copy current state
                loc = source.location.copy()
                loc.x *= -1
                
                rot_q = None
                rot_e = None
                if source.rotation_mode == 'QUATERNION':
                    rot_q = source.rotation_quaternion.copy()
                    rot_q.y *= -1
                    rot_q.z *= -1
                else:
                    rot_e = source.rotation_euler.copy()
                    rot_e.y *= -1
                    rot_e.z *= -1
                
                scale = source.scale.copy()
                
                mirrored_data.append((target_f, loc, rot_q, rot_e, scale))

            # 4. Write data to Target Bone
            for f_time, loc, rot_q, rot_e, scale in mirrored_data:
                scene.frame_set(f_time)
                target.location = loc
                if rot_q: target.rotation_quaternion = rot_q
                if rot_e: target.rotation_euler = rot_e
                target.scale = scale
                
                # Keyframe only the properties that existed
                target.keyframe_insert(data_path="location")
                if rot_q: target.keyframe_insert(data_path="rotation_quaternion")
                if rot_e: target.keyframe_insert(data_path="rotation_euler")
                target.keyframe_insert(data_path="scale")

        scene.frame_set(original_frame)
        self.report({'INFO'}, f"Mirrored {len(bone_pairs)} bones.")
        return {'FINISHED'}

class VIEW3D_PT_MirrorAnimationPanel(bpy.types.Panel):
    bl_label = "Loop Mirror"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.prop(context.window_manager, "mirror_anim_offset", text="Frame Offset")
        col.operator("anim.mirror_keyframes_offset", text="Mirror Selected Keyframes")

classes = (
    ANIM_OT_MirrorKeyframesOffset,
    VIEW3D_PT_MirrorAnimationPanel,
)

def register():
    bpy.types.WindowManager.mirror_anim_offset = bpy.props.IntProperty(
            name="Offset", 
            description="Shift mirrored frames forward", 
            default=0
        )
    
    for my_class in classes:
        bpy.utils.register_class(my_class)
    

def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)
        
    del bpy.types.WindowManager.mirror_anim_offset

if __name__ == "__main__":
    register()