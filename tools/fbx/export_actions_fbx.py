
import bpy
import os

GLOBAL_SCALE=0.74 #scale of the model exported

class EXPORT_OT_vizor_model(bpy.types.Operator):
    """Export Model using (mob_clon2) settings"""
    bl_idname = "export.vizor_model"
    bl_label = "Export Model (mob_clon2)"

    @classmethod
    def poll(cls, context):
        # Check if selection contains both an Armature and a Mesh
        selected = context.selected_objects
        has_armature = any(obj.type == 'ARMATURE' for obj in selected)
        has_mesh = any(obj.type == 'MESH' for obj in selected)
        return has_armature and has_mesh

    def execute(self, context):
        obj = context.active_object

        # Use the name of the first armature found in selection for the filename
        naming_obj = next((o for o in context.selected_objects if o.type == 'ARMATURE'), None)
        if not naming_obj:
            self.report({'ERROR'}, "No Armature found")
            return {'CANCELLED'}

        
        if not context.scene.export_path:
            self.report({'ERROR'}, "Set export path first")
            return {'CANCELLED'}

        export_path = bpy.path.abspath(context.scene.export_path)
        file_path = os.path.join(export_path, naming_obj.name + "_Model.fbx")

        # Settings from mob_clon2.py
        bpy.ops.export_scene.vizor_fbx(
            filepath=file_path,
            use_selection=True,
            use_visible=False,
            use_active_collection=False,
            global_scale=GLOBAL_SCALE, #scale of the model exported
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',
            use_space_transform=True,
            bake_space_transform=True,
            object_types={'ARMATURE', 'MESH'},
            use_mesh_modifiers=True,
            use_mesh_modifiers_render=True,
            mesh_smooth_type='OFF',
            colors_type='SRGB',
            prioritize_active_color=False,
            use_subsurf=False,
            use_mesh_edges=False,
            use_tspace=False,
            use_triangles=False,
            use_custom_props=False,
            add_leaf_bones=False,
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=True,
            armature_nodetype='NULL',
            bake_anim=False,
            bake_anim_use_all_bones=False,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False,
            bake_anim_force_startend_keying=False,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
            path_mode='AUTO',
            embed_textures=False,
            batch_mode='OFF',
            use_batch_own_dir=True,
            axis_forward='-Z',
            axis_up='Y'
        )

        self.report({'INFO'}, f"Model Exported: {obj.name}_Model.fbx")
        return {'FINISHED'}

class EXPORT_OT_vizor_nla_separate(bpy.types.Operator):
    """Export NLA Tracks using (my_HH_export_animation) settings"""
    bl_idname = "export.vizor_nla_separate"
    bl_label = "Export NLA Tracks (my_HH)"
    
    @classmethod
    def poll(cls, context):
        return context.active_object is not None and context.active_object.type == 'ARMATURE' and len(context.selected_objects) == 1

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'ARMATURE' or not obj.animation_data:
            self.report({'ERROR'}, "Select Armature with NLA tracks")
            return {'CANCELLED'}

        if not context.scene.export_path:
            self.report({'ERROR'}, "Set export path first")
            return {'CANCELLED'}

        export_path = bpy.path.abspath(context.scene.export_path)
        if not os.path.exists(export_path): os.makedirs(export_path)

        # Cache state
        original_mute_states = [t.mute for t in obj.animation_data.nla_tracks]
        original_frame_start = context.scene.frame_start
        original_frame_end = context.scene.frame_end

        # Only select the Armature (as per settings: object_types={'ARMATURE'})
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)

        tracks = obj.animation_data.nla_tracks
        for track in tracks:
            if not track.strips: continue
            
            # Solo the track
            for t in tracks: t.mute = True
            track.mute = False
            
            # Set frames
            start_f = min(s.frame_start for s in track.strips)
            end_f = max(s.frame_end for s in track.strips)
            context.scene.frame_start, context.scene.frame_end = int(start_f), int(end_f)
            
            file_name = "".join([c for c in track.name if c.isalnum() or c in (' ', '.', '_')]).rstrip()
            file_path = os.path.join(export_path, file_name + ".fbx")

            # Settings from my_HH_export_animation.py
            bpy.ops.export_scene.vizor_fbx(
                filepath=file_path,
                use_selection=True,
                use_visible=False,
                use_active_collection=False,
                global_scale=GLOBAL_SCALE,
                apply_unit_scale=False,
                apply_scale_options='FBX_SCALE_UNITS',
                use_space_transform=False,
                bake_space_transform=False,
                object_types={'ARMATURE'},
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='OFF',
                colors_type='SRGB',
                prioritize_active_color=False,
                use_subsurf=False,
                use_mesh_edges=False,
                use_tspace=False,
                use_triangles=False,
                use_custom_props=False,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=True,
                armature_nodetype='REMOVE_GHOST',
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,
                bake_anim_use_all_actions=False,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=0.0,
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
                use_batch_own_dir=True,
                axis_forward='Y',
                axis_up='Z'
            )

        # Restore
        for i, track in enumerate(obj.animation_data.nla_tracks):
            track.mute = original_mute_states[i]
        context.scene.frame_start, context.scene.frame_end = original_frame_start, original_frame_end

        self.report({'INFO'}, f"Exported {len(tracks)} Animations")
        return {'FINISHED'}

class EXPORT_OT_vizor_full_mesh_anim(bpy.types.Operator):
    """Export single FBX with Armature + Meshes + All Animations (Single File)"""
    bl_idname = "export.vizor_full_mesh_anim_precise"
    bl_label = "Export Full Model + All Anims"

    @classmethod
    def poll(cls, context):
        selected = context.selected_objects
        has_armature = any(obj.type == 'ARMATURE' for obj in selected)
        has_mesh = any(obj.type == 'MESH' for obj in selected)
        return has_armature and has_mesh

    def execute(self, context):
        naming_obj = next((o for o in context.selected_objects if o.type == 'ARMATURE'), None)
        if not context.scene.export_path:
            self.report({'ERROR'}, "Set export path first")
            return {'CANCELLED'}

        export_path = bpy.path.abspath(context.scene.export_path)
        file_path = os.path.join(export_path, naming_obj.name + "_Full.fbx")

        # 1. STORE EXISTING MUTE STATES
        state_backup = []
        if naming_obj.animation_data and naming_obj.animation_data.nla_tracks:
            for track in naming_obj.animation_data.nla_tracks:
                track_info = {
                    'track': track,
                    'mute': track.mute,
                    'strips': [{'strip': s, 'mute': s.mute} for s in track.strips]
                }
                state_backup.append(track_info)
                
                # 2. ENABLE EVERYTHING FOR EXPORT
                track.mute = False
                for strip in track.strips:
                    strip.mute = False

        # Use Animation Settings (Scale 1.0, Y Forward) but export both Mesh and Armature
        # Includes all animations (NLA Strips + All Actions)
        bpy.ops.export_scene.vizor_fbx(
                filepath=file_path,
                use_selection=True,
                use_visible=False,
                object_types={'ARMATURE', 'MESH'},
                use_active_collection=False,
                global_scale=GLOBAL_SCALE,
                apply_unit_scale=False,
                apply_scale_options='FBX_SCALE_UNITS',
                use_space_transform=False,
                bake_space_transform=False,
                use_mesh_modifiers=True,
                use_mesh_modifiers_render=True,
                mesh_smooth_type='OFF',
                colors_type='SRGB',
                prioritize_active_color=False,
                use_subsurf=False,
                use_mesh_edges=False,
                use_tspace=False,
                use_triangles=False,
                use_custom_props=False,
                add_leaf_bones=False,
                primary_bone_axis='Y',
                secondary_bone_axis='X',
                use_armature_deform_only=True,
                armature_nodetype='REMOVE_GHOST',
                bake_anim=True,
                bake_anim_use_all_bones=True,
                bake_anim_use_nla_strips=True,
                bake_anim_use_all_actions=False,
                bake_anim_force_startend_keying=True,
                bake_anim_step=1.0,
                bake_anim_simplify_factor=0.0,
                path_mode='AUTO',
                embed_textures=False,
                batch_mode='OFF',
                use_batch_own_dir=True,
                axis_forward='Y',
                axis_up='Z'
            )
        
        # 4. REVERT TO STORED MUTE STATES
        for info in state_backup:
            info['track'].mute = info['mute']
            for s_info in info['strips']:
                s_info['strip'].mute = s_info['mute']

        self.report({'INFO'}, f"Full Model Exported: {naming_obj.name}_Full.fbx")
        return {'FINISHED'}

class EXPORT_OT_vizor_active_nla_mesh(bpy.types.Operator):
    """Export the currently UNMUTED NLA track with selected Meshes"""
    bl_idname = "export.vizor_active_nla_mesh"
    bl_label = "Export Active NLA + Mesh"

    @classmethod
    def poll(cls, context):
        selected = context.selected_objects
        has_armature = any(obj.type == 'ARMATURE' for obj in selected)
        has_mesh = any(obj.type == 'MESH' for obj in selected)
        return has_armature and has_mesh

    def execute(self, context):
        arm = next((o for o in context.selected_objects if o.type == 'ARMATURE'), None)
        meshes = [o for o in context.selected_objects if o.type == 'MESH']
        
        if not arm.animation_data or not arm.animation_data.nla_tracks:
            self.report({'ERROR'}, "No NLA data found on Armature")
            return {'CANCELLED'}

        # Find the first track that is not muted
        active_track = next((t for t in arm.animation_data.nla_tracks if not t.mute), None)
        
        if not active_track:
            self.report({'ERROR'}, "No unmuted NLA track found")
            return {'CANCELLED'}

        export_path = bpy.path.abspath(context.scene.export_path)
        file_path = os.path.join(export_path, active_track.name + ".fbx")

        # Sync frame range to track
        orig_start, orig_end = context.scene.frame_start, context.scene.frame_end
        if active_track.strips:
            s_f = min(s.frame_start for s in active_track.strips)
            e_f = max(s.frame_end for s in active_track.strips)
            context.scene.frame_start, context.scene.frame_end = int(s_f), int(e_f)

        bpy.ops.export_scene.vizor_fbx(
            filepath=file_path,
            use_selection=True,
            use_visible=False,
            object_types={'ARMATURE', 'MESH'},
            global_scale=GLOBAL_SCALE,
            apply_unit_scale=False,
            apply_scale_options='FBX_SCALE_UNITS',
            use_space_transform=False,
            bake_space_transform=False,
            mesh_smooth_type='OFF',
            primary_bone_axis='Y',
            secondary_bone_axis='X',
            use_armature_deform_only=True,
            armature_nodetype='REMOVE_GHOST',
            bake_anim=True,
            bake_anim_use_all_bones=True,
            bake_anim_use_nla_strips=True,
            bake_anim_use_all_actions=False, # Only export the active NLA track
            bake_anim_force_startend_keying=True,
            bake_anim_step=1.0,
            bake_anim_simplify_factor=0.0,
            axis_forward='Y',
            axis_up='Z',
            path_mode='AUTO'
        )

        context.scene.frame_start, context.scene.frame_end = orig_start, orig_end
        self.report({'INFO'}, f"Exported Active Track: {active_track.name}.fbx")
        return {'FINISHED'}


class VIEW3D_PT_vizor_exporter_precise(bpy.types.Panel):
    bl_label = "Vizor Batch Exporter"
    bl_idname = "VIEW3D_PT_vizor_exporter_precise"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Batch Export'


    def draw(self, context):
        layout = self.layout
        scene = context.scene

        layout.prop(scene, "export_path", text="Folder")

        layout.label(text=f"Global Scale={GLOBAL_SCALE}")
        
        layout.label(text=f"Export Model FBX:")
        layout.operator(EXPORT_OT_vizor_model.bl_idname, icon='MESH_DATA')
        
        layout.separator()
        
        layout.label(text="Export Animations Separate FBX:")
        layout.operator(EXPORT_OT_vizor_nla_separate.bl_idname, icon='ANIM_DATA')

        layout.separator()
        
        layout.label(text="Export Animations One FBX:")
        layout.operator(EXPORT_OT_vizor_full_mesh_anim.bl_idname, icon='ANIM_DATA')

        layout.separator()
        
        layout.label(text="Export Animations One FBX:")
        layout.operator(EXPORT_OT_vizor_active_nla_mesh.bl_idname, icon='ANIM_DATA')

classes = (
    EXPORT_OT_vizor_active_nla_mesh,
    EXPORT_OT_vizor_model,
    EXPORT_OT_vizor_nla_separate,
    EXPORT_OT_vizor_full_mesh_anim,
    VIEW3D_PT_vizor_exporter_precise,
)

def register():
    bpy.types.Scene.export_path = bpy.props.StringProperty(name="Export Path", subtype='DIR_PATH')
    for my_class in classes:
        bpy.utils.register_class(my_class)
    
def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)
    del bpy.types.Scene.export_path

if __name__ == "__main__":
    register()