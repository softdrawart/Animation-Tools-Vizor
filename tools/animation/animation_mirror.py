import bpy

class ANIM_OT_MirrorLoopComplex(bpy.types.Operator):
    """Mirror animation: Handles complex names, wrap logic, and boundary sync"""
    bl_idname = "anim.mirror_loop_complex"
    bl_label = "Mirror & Sync Loop"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or not obj.animation_data or not obj.animation_data.action:
            self.report({'ERROR'}, "Active object must have an Action")
            return {'CANCELLED'}

        scene = context.scene
        action = obj.animation_data.action
        
        # Determine Loop Boundaries
        start_f = scene.frame_start
        end_f = scene.frame_end
        duration = (end_f - start_f) + 1  # e.g., 0-15 = 16 frames
        loop_end_f = end_f + 1            # Frame 16
        
        offset = context.window_manager.mirror_anim_offset
        selected_bones = context.selected_pose_bones
        original_frame = scene.frame_current

        # 1. Identify Pairs using Blender's flip_name utility
        bone_pairs = []
        for s_bone in selected_bones:
            # flip_name handles "bone.L", "bone.L.001", "n.002.L.001" correctly
            m_name = bpy.utils.flip_name(s_bone.name)
            if m_name != s_bone.name and m_name in obj.pose.bones:
                bone_pairs.append((s_bone, obj.pose.bones[m_name]))

        if not bone_pairs:
            self.report({'ERROR'}, "No mirrored counterparts found for selected bones")
            return {'CANCELLED'}

        for source, target in bone_pairs:
            source_prefix = f'pose.bones["{source.name}"]'
            target_prefix = f'pose.bones["{target.name}"]'
            
            # 2. COLLECT SOURCE METADATA
            source_keyframes = set()
            source_handle_info = {}
            
            source_fcurves = [fc for fc in action.fcurves if fc.data_path.startswith(source_prefix)]
            for fc in source_fcurves:
                prop_key = fc.data_path + str(fc.array_index)
                for kp in fc.keyframe_points:
                    f = int(kp.co.x)
                    source_keyframes.add(f)
                    if f not in source_handle_info: source_handle_info[f] = {}
                    source_handle_info[f][prop_key] = {
                        'interp': kp.interpolation,
                        'left': kp.handle_left_type,
                        'right': kp.handle_right_type
                    }

            # If no keys, skip
            if not source_keyframes: continue

            # 3. SAMPLE POSES (Original keys + Boundary Frames)
            # Find the source frame that will become the Target's Frame 16
            src_for_loopend = start_f + ((-offset) % duration)
            
            required_samples = source_keyframes.copy()
            required_samples.add(src_for_loopend)
            required_samples.add(start_f) # Ensure we have the start too

            MirroredPoses = {}
            for sf in required_samples:
                scene.frame_set(sf)
                
                # Mirror Logic (Standard X-Flip)
                loc = source.location.copy()
                loc.x *= -1
                
                rot_q = source.rotation_quaternion.copy() if source.rotation_mode == 'QUATERNION' else None
                if rot_q:
                    rot_q.y *= -1
                    rot_q.z *= -1
                
                rot_e = source.rotation_euler.copy() if source.rotation_mode != 'QUATERNION' else None
                if rot_e:
                    rot_e.y *= -1
                    rot_e.z *= -1
                
                scale = source.scale.copy()
                MirroredPoses[sf] = {'loc': loc, 'rot_q': rot_q, 'rot_e': rot_e, 'scale': scale}

            # 4. CLEAR TARGET
            target_fcurves = [fc for fc in action.fcurves if fc.data_path.startswith(target_prefix)]
            for fc in target_fcurves:
                action.fcurves.remove(fc)

            # 5. BUILD AND WRAP TARGET KEYS
            # Step A: Process everything into a temporary map
            TargetMap = {}
            for sf in source_keyframes:
                TargetMap[sf + offset] = MirroredPoses[sf]
            
            # Step B: Close the Loop (Calculate 16, then copy to 0)
            TargetMap[loop_end_f] = MirroredPoses[src_for_loopend]
            TargetMap[start_f] = TargetMap[loop_end_f]

            # Step C: Apply to Timeline with Modulo Wrapping
            for tf, pose in TargetMap.items():
                final_tf = tf
                # Wrap frames that fall outside the start_f -> loop_end_f range
                if tf > loop_end_f or tf < start_f:
                    final_tf = start_f + ((tf - start_f) % duration)
                
                scene.frame_set(final_tf)
                target.location = pose['loc']
                if pose['rot_q']: target.rotation_quaternion = pose['rot_q']
                if pose['rot_e']: target.rotation_euler = pose['rot_e']
                target.scale = pose['scale']
                
                target.keyframe_insert(data_path="location")
                if pose['rot_q']: target.keyframe_insert(data_path="rotation_quaternion")
                if pose['rot_e']: target.keyframe_insert(data_path="rotation_euler")
                target.keyframe_insert(data_path="scale")

            # 6. RESTORE HANDLES AND CYCLES
            target_fcurves = [fc for fc in action.fcurves if fc.data_path.startswith(target_prefix)]
            for fc in target_fcurves:
                prop = fc.data_path + str(fc.array_index)
                src_prop = prop.replace(target.name, source.name)
                
                # Add Cycles for infinite playback
                mod = fc.modifiers.new('CYCLES')
                mod.mode_before = 'REPEAT'
                mod.mode_after = 'REPEAT'

                for kp in fc.keyframe_points:
                    tf = int(kp.co.x)
                    # Trace back to original source frame to find handle type
                    sf_raw = tf - offset
                    sf_wrapped = start_f + ((sf_raw - start_f) % duration)
                    
                    if sf_wrapped in source_handle_info and src_prop in source_handle_info[sf_wrapped]:
                        h = source_handle_info[sf_wrapped][src_prop]
                        kp.interpolation = h['interp']
                        kp.handle_left_type = h['left']
                        kp.handle_right_type = h['right']

        scene.frame_set(original_frame)
        self.report({'INFO'}, f"Mirrored {len(bone_pairs)} bones with loop sync.")
        return {'FINISHED'}

class VIEW3D_PT_MirrorAnimationPanel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'
    bl_label = "Loop Mirror Pro"

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        col = layout.column(align=True)
        col.label(text=f"Loop Range: {scene.frame_start} to {scene.frame_end + 1}")
        col.prop(context.window_manager, "mirror_anim_offset", text="Frame Offset")
        col.operator("anim.mirror_loop_complex", text="Mirror & Shift (Wrap Logic)")
classes = (
    ANIM_OT_MirrorLoopComplex,
    VIEW3D_PT_MirrorAnimationPanel,
)

def register():
    bpy.types.WindowManager.mirror_anim_offset = bpy.props.IntProperty(name="Offset", default=0)
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.register_class(cls)
    del bpy.types.WindowManager.mirror_anim_offset

if __name__ == "__main__":
    register()