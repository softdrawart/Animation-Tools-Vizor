
import bpy

def get_all_fcurves(action):
    """Safely retrieve F-Curves for both Blender 4.x and 5.0+ Slotted Actions."""
    curves = []
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    curves.extend(channelbag.fcurves)
    elif hasattr(action, "fcurves"):
        curves.extend(action.fcurves)
    return curves

class ANIM_OT_stagger_keyframes(bpy.types.Operator):
    bl_idname = "anim.stagger_keyframes"
    bl_label = "Stagger Keyframes"
    bl_description = "Shift keyframes incrementally across selected bones based on hierarchy"
    bl_options = {'REGISTER', 'UNDO'}

    offset_amount: bpy.props.FloatProperty(
        name="Offset Frames",
        description="Number of frames to shift each successive bone",
        default=1.0,
    )

    reverse_order: bpy.props.BoolProperty(
        name="Reverse Order",
        description="Shift from tip to root instead of root to tip",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.type == 'ARMATURE' and context.mode == 'POSE'

    def execute(self, context):
        obj = context.active_object
        anim_data = obj.animation_data
        
        if not anim_data or not anim_data.action:
            self.report({'WARNING'}, "No animation data found on the active armature.")
            return {'CANCELLED'}

        # Gather selected bones
        selected_bones = [b for b in context.selected_pose_bones]
        if not selected_bones:
            self.report({'WARNING'}, "No bones selected. Select a chain of bones in Pose Mode.")
            return {'CANCELLED'}

        # Calculate hierarchical depth to ensure root-to-tip ordering
        def get_depth(bone):
            depth = 0
            parent = bone.parent
            while parent:
                depth += 1
                parent = parent.parent
            return depth

        selected_bones.sort(key=lambda b: get_depth(b.bone), reverse=self.reverse_order)

        fcurves = get_all_fcurves(anim_data.action)
        shifted_count = 0

        for index, pbone in enumerate(selected_bones):
            shift = index * self.offset_amount
            if shift == 0:
                continue
            
            data_path_prefix = f'pose.bones["{pbone.name}"]'
            bone_curves = [fc for fc in fcurves if fc.data_path.startswith(data_path_prefix)]
            
            if bone_curves:
                shifted_count += 1
                for fcurve in bone_curves:
                    for kp in fcurve.keyframe_points:
                        kp.co.x += shift
                        kp.handle_left.x += shift
                        kp.handle_right.x += shift
                    fcurve.update()

        self.report({'INFO'}, f"Staggered {shifted_count} bones with a {self.offset_amount}-frame offset.")
        return {'FINISHED'}

class ANIM_PT_stagger_panel(bpy.types.Panel):
    bl_label = "Anim Stagger"
    bl_idname = "ANIM_PT_stagger_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        if context.mode != 'POSE':
            layout.label(text="Enter Pose Mode to use.")
            return
        
        op = layout.operator("anim.stagger_keyframes", text="Stagger Selected Bones")
        # Default properties can be set here if needed, but the operator will 
        # prompt the user with a dialog/redo panel for the offset amount.

def register():
    bpy.utils.register_class(ANIM_OT_stagger_keyframes)
    bpy.utils.register_class(ANIM_PT_stagger_panel)

def unregister():
    bpy.utils.unregister_class(ANIM_PT_stagger_panel)
    bpy.utils.unregister_class(ANIM_OT_stagger_keyframes)

if __name__ == "__main__":
    register()