
import bpy

class ANIM_OT_bake_to_markers(bpy.types.Operator):
    """Keyframe selected bones at markers and remove all other frames"""
    bl_idname = "anim.bake_to_markers"
    bl_label = "Bake Selected to Markers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (context.active_object and 
                context.active_object.type == 'ARMATURE' and 
                context.selected_pose_bones)

    def execute(self, context):
        obj = context.active_object
        scene = context.scene
        selected_bones = context.selected_pose_bones
        
        # FIX: Use timeline_markers instead of markers
        marker_frames = {m.frame for m in scene.timeline_markers}

        if not marker_frames:
            self.report({'WARNING'}, "No markers found in the timeline.")
            return {'CANCELLED'}

        # 1. Add keyframes at every marker frame
        original_frame = scene.frame_current
        
        for frame in marker_frames:
            scene.frame_set(frame)
            for bone in selected_bones:
                # Key Location, Rotation, and Scale
                bone.keyframe_insert(data_path="location")
                
                if bone.rotation_mode == 'QUATERNION':
                    bone.keyframe_insert(data_path="rotation_quaternion")
                elif bone.rotation_mode == 'AXIS_ANGLE':
                    bone.keyframe_insert(data_path="rotation_axis_angle")
                else:
                    bone.keyframe_insert(data_path="rotation_euler")
                    
                bone.keyframe_insert(data_path="scale")

        # 2. Cleanup: Remove keyframes not on marker frames
        if obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            bone_names = [f'pose.bones["{b.name}"]' for b in selected_bones]
            
            for fcurve in action.fcurves:
                # Check if this F-Curve belongs to one of the selected bones
                if any(fcurve.data_path.startswith(bone_path) for bone_path in bone_names):
                    points = fcurve.keyframe_points
                    # Iterate backwards to safely remove while looping
                    for i in range(len(points) - 1, -1, -1):
                        kp = points[i]
                        # If the keyframe frame is not in our marker set
                        if round(kp.co.x) not in marker_frames:
                            points.remove(kp)
                    
                    fcurve.update()

        # Restore original frame
        scene.frame_set(original_frame)
        self.report({'INFO'}, f"Baked {len(selected_bones)} bones to {len(marker_frames)} markers.")
        return {'FINISHED'}

class ANIM_PT_marker_bake_panel(bpy.types.Panel):
    """Creates a Panel in the View3D Sidebar"""
    bl_label = "Marker Baker"
    bl_idname = "ANIM_PT_marker_bake"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("anim.bake_to_markers", icon='MARKER')

classes = (
    ANIM_OT_bake_to_markers,
    ANIM_PT_marker_bake_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()