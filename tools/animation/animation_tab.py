

import bpy, bmesh
from mathutils import Vector, kdtree
import math, os

######################################################
# Panel

class VIZOR_ANIMATION_PT_VIZOR(bpy.types.Panel):
    bl_idname = 'VIZOR_ANIMATION_PT_VIZOR'
    bl_label = 'Vizor Animation Panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        
        box = layout.box()
        box.operator(RESET_STRETCH_OT_VIZOR.bl_idname, text = "Reset Stretch Constraints")
        box.operator(RESET_TRANSFORM_OT_VIZOR.bl_idname, text = "Reset Transforms")
        box.operator(CLEAR_VGROUPS_OT_VIZOR.bl_idname, text = "Clear Vertex Groups")
        box.operator(MOVE_ARMATURE_UP_OT_VIZOR.bl_idname, text = "Move Armatures Up")
        box.operator(SELECT_DEF_BONES_OT_VIZOR.bl_idname, text = "Select Deformation Bones")
        box.operator(SELECT_CTRL_BONES_OT_VIZOR.bl_idname, text = "Select Controller Bones")
        box.operator(COPY_BONES_POSITION_OT_VIZOR.bl_idname, text = "Copy Bones Position")
        box.operator(SELECT_VGROUP_BONES_OT_VIZOR.bl_idname, text = "Select Vertex Group Bones")
        box.operator(COPY_SHAPE_KEYS_OT_VIZOR.bl_idname, text = "Copy All Shape Keys")
        box.operator(CLEAR_MISSING_CHANNELS_OT_VIZOR.bl_idname, text = "Clear Missing Channels")
        box.operator(OFFSET_KEYFRAMES_OT_VIZOR.bl_idname, text = "Offset selected channels keyframes")
        box.operator(MIRROR_WEIGHTS_OT_VIZOR.bl_idname, text = "Mirror Weights")
        box.operator(REMOVE_CORRUPTED_PACKED_FILES_OT_VIZOR.bl_idname, text = "Remove Corrupted Images")
        box.operator(CLEAR_EMMPTY_WEIGHTS_OT_VIZOR.bl_idname, text = "Remove empty weights")
        box.operator(COLLECT_WGTS_OT_VIZOR.bl_idname, text = "Collect WGTs")
        box.operator(APPLY_ARMATURE_OT_VIZOR.bl_idname, text = "Apply Armature Modifiers")
        box.operator(FIND_CONCAVE_POLY_OT_VIZOR.bl_idname, text = "Find Concave Polygons")
        box.operator(COPY_NLA_OT_VIZOR.bl_idname, text = "Copy NLA")
        box.operator(SCALE_ANIMATION_OT_VIZOR.bl_idname, text = "Scale Animation")
        box.operator(CONNECT_BONES_TO_MESH_OT_VIZOR.bl_idname, text = "Connect bones to mesh")
        box.operator(TRANSFER_WEIGHTS_TO_LATTICE_OT_VIZOR.bl_idname, text = "Transfer mesh weights to lattice")
        box.operator(OBJECT_OT_surface_deform_setup.bl_idname, text = "Surface Deform selected objects")
        box.operator(CLEAN_UP_SCENE_OT_VIZOR.bl_idname, text = "Clean up Scene")
        box.operator(ALIGN_TO_WORLD_AXIS_OT_VIZOR.bl_idname, text = "Align to world axis")
        box.operator(ANIM_OT_clean_bone_channels_VIZOR.bl_idname, text = "Remove extra channels")
        box.operator(ResetIKStretch_OT_VIZOR.bl_idname, text = "Reset IK Stretch")
        box.operator(POSE_OT_MaintainVolumeAnimation_OR_VIZOR.bl_idname, text = "Maintain Volume Animation")
        box.operator(POSE_SwapAnimationChannels_OT_VIZOR.bl_idname, text = "Swap animation channels")
        box.operator(IMAGE_downscale_all_OT_VIZOR.bl_idname, text = "Downscale images")
        box.operator(NLA_SetPreviewRangeToStrips_OT_VIZOR.bl_idname, text = "Set Animation Range to NLA track")
        box.operator(MESH_RemoveNonDeformVGroups_OT_VIZOR.bl_idname, text = "Remove Non-Deform Vertex Groups")
        
        
        
        
        
######################################################
# Operators

class NLA_SetPreviewRangeToStrips_OT_VIZOR(bpy.types.Operator):
    """Set the Scene Preview Range to match the span of selected NLA strips"""
    bl_idname = "nla.set_preview_range_to_selected"
    bl_label = "Set Preview Range to Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only enable button if there is an active armature object
        return context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        obj = context.active_object
        
        if not obj.animation_data or not obj.animation_data.nla_tracks:
            self.report({'WARNING'}, "No NLA tracks found on active object")
            return {'CANCELLED'}

        # Collect all selected strips across all tracks
        selected_strips = []
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.select:
                    selected_strips.append(strip)

        if not selected_strips:
            self.report({'WARNING'}, "No NLA strips selected")
            return {'CANCELLED'}

        # Calculate the min start and max end
        start_frame = min(s.frame_start for s in selected_strips)
        end_frame = max(s.frame_end for s in selected_strips)

        # Apply to scene preview range
        scene = context.scene
        scene.use_preview_range = True
        scene.frame_preview_start = int(start_frame)
        scene.frame_preview_end = int(end_frame)

        self.report({'INFO'}, f"Range set: {scene.frame_preview_start} to {scene.frame_preview_end}")
        return {'FINISHED'}

class IMAGE_downscale_all_OT_VIZOR(bpy.types.Operator):
    """Downscale all external images to a maximum resolution and overwrite them"""
    bl_label = "Downscale All Textures"
    bl_idname = "image.downscale_all"
    bl_options = {'REGISTER', 'UNDO'}

    max_size: bpy.props.IntProperty(
        name="Max Resolution",
        description="The maximum width or height for any texture",
        default=1024,
        min=1,
        soft_min=128
    )

    @classmethod
    def poll(cls, context):
        # 1. Check if Auto-pack is ON (The user requested it be OFF)
        if bpy.data.use_autopack:
            cls.poll_message_set("Operation cancelled: Disable 'Automatically Pack Resources' in File > External Data.")
            return False

        # 2. Check if any images are packed or missing
        for img in bpy.data.images:
            if img.source == 'FILE':
                # Check if packed
                if img.packed_file:
                    cls.poll_message_set(f"Operation cancelled: Image '{img.name}' is packed. Unpack all files first.")
                    return False
                
                # Check if file exists/is not corrupt (size 0,0 indicates a bad load)
                if img.size[0] == 0 or img.size[1] == 0:
                    cls.poll_message_set(f"Operation cancelled: Image '{img.name}' is corrupt or missing.")
                    return False
        
        return True

    def execute(self, context):
        processed_count = 0
        error_count = 0

        for image in bpy.data.images:
            # Only process external files, ignore render results/generated textures
            if image.source == 'FILE' and image.filepath:
                
                width, height = image.size[0], image.size[1]
                current_max = max(width, height)

                if current_max > self.max_size:
                    # Calculate new dimensions preserving aspect ratio
                    ratio = self.max_size / current_max
                    new_width = int(width * ratio)
                    new_height = int(height * ratio)

                    self.report({'INFO'}, f"Resizing '{image.name}' to {new_width}x{new_height}")

                    try:
                        # Scale the image in Blender's memory
                        image.scale(new_width, new_height)

                        # Determine file format for saving
                        ext = os.path.splitext(image.filepath)[1].lower()
                        if ext in ['.jpg', '.jpeg']:
                            image.file_format = 'JPEG'
                        elif ext == '.png':
                            image.file_format = 'PNG'
                        elif ext == '.tga':
                            image.file_format = 'TARGA'
                        elif ext == '.tiff':
                            image.file_format = 'TIFF'
                        
                        # Save the scaled image back to the original path
                        image.save()
                        processed_count += 1

                    except Exception as e:
                        self.report({'ERROR'}, f"Failed to save {image.name}: {str(e)}")
                        error_count += 1

        self.report({'INFO'}, f"Processed {processed_count} images. Errors: {error_count}")
        return {'FINISHED'}

class POSE_SwapAnimationChannels_OT_VIZOR(bpy.types.Operator):
    """Swap existing animation F-Curves between two channels for selected bones"""
    bl_idname = "pose.swap_animation_channels"
    bl_label = "Swap Bone Channels"
    bl_options = {'REGISTER', 'UNDO'}

    transform_type: bpy.props.EnumProperty(
        name="Transform",
        items=[
            ('location', "Location", "Swap Location (XYZ)"),
            ('rotation_euler', "Rotation (Euler)", "Swap Euler (XYZ)"),
            ('rotation_quaternion', "Rotation (Quaternion)", "Swap Quaternion (WXYZ)"),
            ('scale', "Scale", "Swap Scale (XYZ)")
        ],
        default='location'
    )

    channel_a: bpy.props.EnumProperty(
        name="Channel A",
        items=[('0', "0", ""), ('1', "1", ""), ('2', "2", ""), ('3', "3", "")]
    )

    channel_b: bpy.props.EnumProperty(
        name="Channel B",
        items=[('0', "0", ""), ('1', "1", ""), ('2', "2", ""), ('3', "3", "")],
        default='1'
    )

    flip_a: bpy.props.BoolProperty(name="Flip A", description="Multiply A's values by -1", default=False)
    flip_b: bpy.props.BoolProperty(name="Flip B", description="Multiply B's values by -1", default=False)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "transform_type")
        
        is_quat = self.transform_type == 'rotation_quaternion'
        labels = ["W", "X", "Y", "Z"] if is_quat else ["X", "Y", "Z", "N/A"]
        
        box = layout.box()
        # Channel A Row
        row = box.row(align=True)
        row.label(text="Channel A:")
        for i in range(4 if is_quat else 3):
            row.prop_enum(self, "channel_a", str(i), text=labels[i])
        
        # Channel B Row
        row = box.row(align=True)
        row.label(text="Channel B:")
        for i in range(4 if is_quat else 3):
            row.prop_enum(self, "channel_b", str(i), text=labels[i])

        split = layout.split()
        split.prop(self, "flip_a")
        split.prop(self, "flip_b")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return (obj and obj.type == 'ARMATURE' and 
                context.selected_pose_bones and 
                obj.animation_data and obj.animation_data.action)

    def apply_flip(self, fcurve):
        """Multiplies all keyframe values and handles of an F-Curve by -1"""
        for kp in fcurve.keyframe_points:
            kp.co[1] *= -1.0
            kp.handle_left[1] *= -1.0
            kp.handle_right[1] *= -1.0
        fcurve.update()

    def execute(self, context):
        action = context.active_object.animation_data.action
        idx_a = int(self.channel_a)
        idx_b = int(self.channel_b)

        if idx_a == idx_b:
            self.report({'WARNING'}, "Channels are the same.")
            return {'CANCELLED'}

        # Validate index for non-quats
        if self.transform_type != 'rotation_quaternion' and (idx_a > 2 or idx_b > 2):
            self.report({'ERROR'}, "Index 3 (W) is only for Quaternions.")
            return {'CANCELLED'}

        for bone in context.selected_pose_bones:
            data_path = f'pose.bones["{bone.name}"].{self.transform_type}'
            
            # Find existing F-Curves
            f_a = action.fcurves.find(data_path, index=idx_a)
            f_b = action.fcurves.find(data_path, index=idx_b)

            if not f_a and not f_b:
                continue

            # 1. Handle Flipping on the existing objects
            if f_a and self.flip_a:
                self.apply_flip(f_a)
            if f_b and self.flip_b:
                self.apply_flip(f_b)

            # 2. Swap the array_index
            # If both exist, we need a temporary index to avoid path collision
            if f_a and f_b:
                f_a.array_index = 99  # Temporary unique index
                f_b.array_index = idx_a
                f_a.array_index = idx_b
            elif f_a:
                # Only A exists, move it to slot B
                f_a.array_index = idx_b
            elif f_b:
                # Only B exists, move it to slot A
                f_b.array_index = idx_a

        # Update the UI and animation system
        context.area.tag_redraw()
        return {'FINISHED'}

class ANIM_OT_clean_bone_channels_VIZOR(bpy.types.Operator):
    """Remove all F-Curve channels except Loc/Rot/Scale for selected bones"""
    bl_idname = "pose.clean_bone_channels"
    bl_label = "Keep Only Transform Channels"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Must be in Pose Mode with an active armature and selected bones
        return (context.mode == 'POSE' and 
                context.active_object and 
                context.active_object.type == 'ARMATURE' and 
                context.selected_pose_bones)

    def execute(self, context):
        obj = context.active_object
        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No Action found on Armature")
            return {'CANCELLED'}

        action = obj.animation_data.action
        selected_bone_names = [b.name for b in context.selected_pose_bones]
        
        # Transformation keywords to keep
        keep_keywords = ["location", "rotation_quaternion", "rotation_euler", "scale"]
        
        # We iterate backwards to safely remove items from the collection
        fcurves = action.fcurves
        initial_count = len(fcurves)
        
        for i in range(len(fcurves) - 1, -1, -1):
            fcurve = fcurves[i]
            data_path = fcurve.data_path
            
            # Check if this F-Curve belongs to one of our selected bones
            # Path format: pose.bones["BoneName"].channel
            if any(f'pose.bones["{name}"]' in data_path for name in selected_bone_names):
                
                # Check if it's a transform channel
                is_transform = any(k in data_path for k in keep_keywords)
                
                if not is_transform:
                    fcurves.remove(fcurve)

        self.report({'INFO'}, f"Cleaned {initial_count - len(fcurves)} non-transform channels.")
        return {'FINISHED'}

class RESET_STRETCH_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.reset_stretch"
    bl_label = "Reset Stretch Parameter of all selected bones"
    bl_description = "Reset Stretch Parameter of all selected bones"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        bones = context.selected_pose_bones
        if bones and context.object.mode == 'POSE':
            for b in context.selected_pose_bones:
                for c in b.constraints:
                    if c.name == "Stretch To" or c.name == "Stretch To.001" or c.name == "Stretch To.002" or c.name == "Растяжение" or c.name == "Растяжение.001" or c.name == "Растяжение.002":
                        c.rest_length = 0
                        print(f"reset pose bone: {b.name} constraint: {c.name}")
        else:
            print("Please select pose bones!")
            return {'CANCELLED'}
        return {'FINISHED'}

class RESET_TRANSFORM_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.reset_transforms"
    bl_label = "Reset Geometry Transformation, remove shape keys, and clear parents"
    bl_description = "Reset Geometry Transformation, remove shape keys, and clear parents"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the selected objects
        selected_objects = bpy.context.selected_objects.copy()  # Make a copy of the list
        if not selected_objects:
            print("No objects selected!")
            return {'CANCELLED'}

        for obj in selected_objects:
            hasNodes = False
            modifiers = []
            # Deselect all selected objects and re-select and re-activate the obj
            bpy.ops.object.select_all(action='DESELECT')
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            for mod in obj.modifiers:
                if mod.type == 'NODES':
                    hasNodes = True
                    break
                elif mod.type == 'MIRROR' or mod.type == 'ARMATURE':
                    modifiers.append(mod)
                    print(f"apply {mod.type} on object: {obj.name}")
            if hasNodes:
                # Clear parent
                bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
                print(f"clear parent relationship on object: {obj.name}")
                break
            if modifiers:
                # Apply mirror modifiers and shape keys
                for modifier in modifiers:
                    if obj.data.shape_keys:
                        bpy.ops.object.shape_key_remove(all=True, apply_mix=True)
                        print(f"apply shape keys for object: {obj.name}")
                    bpy.ops.object.modifier_apply(modifier=modifier.name)
                    print(f"apply modifier: {modifier.name} for object: {obj.name}")
            # Clear parent
            bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
            print(f"clear parent relationship on object: {obj.name}")
            # Apply scale and rotation
            bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
            print(f"apply transforms for object: {obj.name}")
            
        return {'FINISHED'}

class CLEAR_VGROUPS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.clear_vertex_groups"
    bl_label = "remove all vertex groups"
    bl_description = "remove all vertex groups"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        objects = context.selected_objects
        if objects:
            for obj in objects:
                obj.vertex_groups.clear()
                print(f"removed all vertex groups for object: {obj.name}")
            return {'FINISHED'}
        else:
            print("No objects selected!")
            return {'CANCELLED'}

class MOVE_ARMATURE_UP_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.move_armature_up"
    bl_label = "move armature modifier up the stack"
    bl_description = "move armature modifier up the stack"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        objects = context.selected_editable_objects
        if objects:
            for obj in objects:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                for arm_mod in [m.name for m in obj.modifiers if 'armature' in m.name.lower() or 'арматура' in m.name.lower()]:
                    bpy.ops.object.modifier_move_to_index(modifier=arm_mod, index=0)
                    #for mod in reversed(obj.modifiers):
                    #    while obj.modifiers.find(arm_mod) != 0:
                    #        bpy.ops.object.modifier_move_up({'object': obj}, modifier=arm_mod)
                    print(f"moved Armature modifier: {arm_mod} up for object: {obj.name}")
            return {'FINISHED'}
        else:
            return {'CANCELLED'}

class SELECT_VGROUP_BONES_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.select_vgroup_bones"
    bl_label = "select all deformation bones of the mesh"
    bl_description = "select all deformation bones of the mesh"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the selected armature and mesh
        armature = None
        mesh = None
        
        if (len(context.selected_objects) == 2):
            if (context.selected_objects[0].type == 'ARMATURE'):
                armature = context.selected_objects[0]
            elif (context.selected_objects[1].type == 'ARMATURE'):
                armature = context.selected_objects[1]
            if (context.selected_objects[1].type == 'MESH'):
                mesh = context.selected_objects[1]
            elif (context.selected_objects[0].type == 'MESH'):
                mesh = context.selected_objects[0]
            print(f'armature object: {armature.name} and mesh object: {mesh.name} selected!')
        else:
            print('plese select two objects mesh and armature')
            return {'CANCELLED'}
        if (armature and mesh):
            #de-select all pose bones
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            # Loop through the vertex groups
            armature_bones = armature.pose.bones
            for group in mesh.vertex_groups:
                group_name = group.name
                # Check if the bone with the same name as the vertex group exists
                if group_name in armature_bones and armature_bones[group_name].bone.use_deform == True:
                    # Select the bone
                    armature_bones[group_name].bone.select = True
                    print(f'selected pose bone: {group_name}')
            return {'FINISHED'}
        else:
            print('plse select a mesh and armature')
            return {'CANCELLED'}

class SELECT_DEF_BONES_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.select_def_bones"
    bl_label = "select all bones with ctrl prefix or shape assigned"
    bl_description = "select all bones with ctrl prefix or shape assigned"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the selected armature
        armature = None
        
        if (len(context.selected_objects) == 1):
            if (context.selected_objects[0].type == 'ARMATURE'):
                armature = context.selected_objects[0]
            else:
                print('plese select armature object!')
                return {'CANCELLED'}
            print(f'armature object: {armature.name} selected!')
        else:
            print('plese select only one object armature type')
            return {'CANCELLED'}
        if (armature):
            #de-select all pose bones
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            # Loop through the bones and check
            for bone in armature.pose.bones:
                # Check if the bone has ctrl in name of has a shape assigned
                if 'def' in bone.name.lower() or bone.bone.use_deform == True:
                    # Select the bone
                    bone.bone.select = True
                    print(f'selected def pose bone: {bone.name}')
            return {'FINISHED'}
        else:
            print('plse select at least one armature object')
            return {'CANCELLED'}

class SELECT_CTRL_BONES_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.select_ctrl_bones"
    bl_label = "select all bones with ctrl prefix or shape assigned"
    bl_description = "select all bones with ctrl prefix or shape assigned"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the selected armature
        armature = None
        
        if (len(context.selected_objects) == 1):
            if (context.selected_objects[0].type == 'ARMATURE'):
                armature = context.selected_objects[0]
            else:
                print('plese select armature object!')
                return {'CANCELLED'}
            print(f'armature object: {armature.name} selected!')
        else:
            print('plese select only one object armature type')
            return {'CANCELLED'}
        if (armature):
            #de-select all pose bones
            bpy.ops.object.select_all(action='DESELECT')
            armature.select_set(True)
            context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            
            # Loop through the bones and check
            for bone in armature.pose.bones:
                # Check if the bone has ctrl in name of has a shape assigned
                if 'ctrl' in bone.name.lower() or bone.custom_shape:
                    # Select the bone
                    bone.bone.select = True
                    print(f'selected ctrl pose bone: {bone.name}')
            return {'FINISHED'}
        else:
            print('plse select at least one armature object')
            return {'CANCELLED'}

class COPY_BONES_POSITION_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.copy_bones_position"
    bl_label = "copy bone position from selected to active"
    bl_description = "copy bone position from selected to active"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the selected armature
        selected_objects = context.selected_objects
        selected_armature = None
        active_armature = context.active_object
        
        if (len(context.selected_objects) == 2):
            if (selected_objects[0].type == 'ARMATURE' and selected_objects[1].type == 'ARMATURE'):
                if(selected_objects[0] != active_armature):
                    selected_armature = selected_objects[0]
                else:
                    selected_armature = selected_objects[1]
            else:
                print('plese select armature objects!')
                return {'CANCELLED'}
        else:
            print('plese select only two armatures')
            return {'CANCELLED'}
        
        # Enter edit mode for the active armature
        bpy.ops.object.mode_set(mode='EDIT')

        # Iterate over each bone in the selected armature
        for selected_bone in selected_armature.data.bones:
            # Find the corresponding bone in the active armature
            active_bone = active_armature.data.edit_bones.get(selected_bone.name)

            # If the bone exists in both armatures, copy the head and tail positions
            if active_bone:
                active_bone.head = selected_bone.head_local
                active_bone.tail = selected_bone.tail_local

        # Exit edit mode
        bpy.ops.object.mode_set(mode='OBJECT')
        return {'FINISHED'}

class COPY_SHAPE_KEYS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.copy_shape_keys"
    bl_label = "Copy Shape Keys from Active to Selected"
    bl_description = "Copy all shape keys (and drivers) from the active object to the other selected objects"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if len(context.selected_objects) < 2:
            return False
        return all(obj.type == 'MESH' for obj in context.selected_objects)
    
    def execute(self, context):
        source = context.active_object
        dests = [obj for obj in context.selected_objects if obj != source]
        
        if not source.data.shape_keys:
            self.report({'WARNING'}, f"Source object {source.name} has no shape keys!")
            return {'CANCELLED'}

        source_shapes = source.data.shape_keys.key_blocks

        for dest in dests:
            # Ensure destination has Basis
            if not dest.data.shape_keys:
                dest.shape_key_add(name="Basis", from_mix=False)

            dest_shapes = dest.data.shape_keys.key_blocks

            # Copy each shape key (excluding Basis)
            for i in range(1, len(source_shapes)):
                shp = source_shapes[i]
                shp_name = shp.name

                # Overwrite existing shape key if necessary
                if shp_name in dest_shapes:
                    dest.shape_key_remove(dest_shapes[shp_name])

                # Create new shape key on dest
                new_key = dest.shape_key_add(name=shp_name, from_mix=False)
                
                # Copy vertex positions
                new_key.data.foreach_set("co", [co for v in shp.data for co in v.co])

                # Copy mute flag
                new_key.mute = shp.mute

                # ---- Copy driver if exists ----
                if source.data.shape_keys.animation_data:
                    data_path = f'key_blocks["{shp_name}"].value'
                    source_driver = source.data.shape_keys.animation_data.drivers.find(data_path)
                    if source_driver:
                        dest_driver = dest.data.shape_keys.driver_add(data_path).driver
                        dest_driver.expression = source_driver.driver.expression
                        dest_driver.type = source_driver.driver.type

                        for var in source_driver.driver.variables:
                            dest_var = dest_driver.variables.new()
                            dest_var.name = var.name
                            dest_var.type = var.type
                            for i, target in enumerate(var.targets):
                                dest_var.targets[i].id = target.id
                                dest_var.targets[i].data_path = target.data_path
                                dest_var.targets[i].transform_type = target.transform_type
                                dest_var.targets[i].transform_space = target.transform_space

                self.report({'INFO'}, f"Copied Shape Key {shp_name} to {dest.name}")

            # Disable soloing if it was enabled
            if dest.show_only_shape_key:
                dest.show_only_shape_key = False

        return {'FINISHED'}


class CLEAR_MISSING_CHANNELS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.clear_missing_channels"
    bl_label = "clears missing channels from active Armature object"
    bl_description = "clears missing channels from active Armature object"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the active action in the Action Editor
        action = context.object.animation_data.action

        # Create a list to store the channels to remove
        channels_to_remove = []

        # Iterate over each F-Curve in the action
        for fcurve in action.fcurves:
            # Check if the RNA data path contains "pose.bones"
            if "pose.bones" in fcurve.data_path:
                # Extract the bone name from the RNA data path
                bone_name = fcurve.data_path.split('"')[1]

                # Check if the bone exists in the armature
                if bone_name not in context.object.pose.bones:
                    channels_to_remove.append(fcurve)

        # Remove the channels with missing pose bones
        for fcurve in channels_to_remove:
            action.fcurves.remove(fcurve)
        return {'FINISHED'}

class OFFSET_KEYFRAMES_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.offset_keyframes"
    bl_label = "offsets selected channels keyframes based on the first keyframe"
    bl_description = "offsets selected channels keyframes based on the first keyframe"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the active object
        obj = context.active_object

        # Get the selected channels
        selected_channels = [f for f in obj.animation_data.action.fcurves if f.select and f.keyframe_points[0].co[0] == -1 and f.keyframe_points[0].select_control_point]
        
        if selected_channels is None:
            print("plese select animation channels!")
            return {'CANCELLED'}
        
        # Loop through each selected keyframe only if it has more than two keys
        for channel in [channel for channel in selected_channels if len(channel.keyframe_points) > 1]:
            
            # Get the previous keyframe of the current track's channel
            first_keyframe = channel.keyframe_points[0].co[1]
            second_keyframe = channel.keyframe_points[1].co[1]
            
            # Calculate the offset value
            offset = first_keyframe - second_keyframe
            
            # Shift the selected keyframes of that channel by the calculated offset
            for keyframe in channel.keyframe_points[1:]:
                keyframe.co_ui[1] += offset
                
        return {'FINISHED'}

class MIRROR_WEIGHTS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.mirror_skin_weights"
    bl_label = "mirror all skin weights"
    bl_description = "mirror all skin weights"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Get the active object (assuming it's a mesh)
        obj = bpy.context.active_object

        if obj.type != 'MESH':
            print(f"Selected object {obj.name} is not a mesh. Aborting.")
            return {'CANCELLED'}

        # Get the mesh data
        mesh = obj.data

        # Create a list to store the vertex group names
        vertex_group_names = [group.name for group in obj.vertex_groups]

        # Loop through the vertex group names
        for old_group_name in vertex_group_names:
            new_group_name = None
            # Check if the group name contains either '.L' or '.R'
            if '.L' in old_group_name:
                new_group_name = old_group_name.replace('.L', '.R')
                if new_group_name in vertex_group_names:
                    continue
            elif '.R' in old_group_name:
                new_group_name = old_group_name.replace('.R', '.L')
                if new_group_name in vertex_group_names:
                    continue
            elif 'Left' in old_group_name:
                new_group_name = old_group_name.replace('Left', 'Right')
                if new_group_name in vertex_group_names:
                    continue
            elif 'Right' in old_group_name:
                new_group_name = old_group_name.replace('Right', 'Left')
                if new_group_name in vertex_group_names:
                    continue
            else:
                continue
                
            # Set the current vertex group as active
            bpy.ops.object.vertex_group_set_active(group=old_group_name)

            # Copy the current vertex group
            bpy.ops.object.vertex_group_copy()

            # Mirror the vertex group using topology
            bpy.ops.object.vertex_group_mirror(use_topology=False)

            # Rename the new mirrored vertex group
            bpy.context.active_object.vertex_groups.active.name = new_group_name
            print(f"Weight group {new_group_name} mirrored and duplicated.")
            
        return {'FINISHED'}

class ALIGN_TO_WORLD_AXIS_OT_VIZOR(bpy.types.Operator):
    """Aligns the active edit bone to a specified world axis, keeping its head in place"""
    bl_idname = "armature.align_bone_to_world_axis"
    bl_label = "Align Bone to World Axis"
    bl_options = {'REGISTER', 'UNDO'}

    axis: bpy.props.EnumProperty(
        name="Axis",
        description="World axis to align the bone with",
        items=[
            ('X_POSITIVE', "X+", "Align along the positive World X-axis"),
            ('X_NEGATIVE', "X-", "Align along the negative World X-axis"),
            ('Y_POSITIVE', "Y+", "Align along the positive World Y-axis"),
            ('Y_NEGATIVE', "Y-", "Align along the negative World Y-axis"),
            ('Z_POSITIVE', "Z+", "Align along the positive World Z-axis"),
            ('Z_NEGATIVE', "Z-", "Align along the negative World Z-axis"),
        ],
        default='Y_POSITIVE',
    )

    @classmethod
    def poll(cls, context):
        """Checks if the operator can run in the current context."""
        return (
            context.object is not None and
            context.object.type == 'ARMATURE' and
            context.mode == 'EDIT_ARMATURE' and
            context.active_bone is not None
        )

    def execute(self, context):
        """The main logic of the operator."""
        # 1. Map the enum property to a corresponding world vector
        axis_map = {
            'X_POSITIVE': Vector((1, 0, 0)),
            'X_NEGATIVE': Vector((-1, 0, 0)),
            'Y_POSITIVE': Vector((0, 1, 0)),
            'Y_NEGATIVE': Vector((0, -1, 0)),
            'Z_POSITIVE': Vector((0, 0, 1)),
            'Z_NEGATIVE': Vector((0, 0, -1)),
        }
        target_vector = axis_map[self.axis]

        # 2. Get necessary data from the context
        armature_obj = context.object
        edit_bone = context.active_bone

        # 3. Store the bone's original length
        bone_length = edit_bone.length
        if bone_length < 1e-6: # Check for near-zero length
            self.report({'WARNING'}, "Cannot align a bone with zero length.")
            return {'CANCELLED'}

        # 4. Get the armature's world matrix to handle transformations
        armature_matrix = armature_obj.matrix_world
        armature_matrix_inverted = armature_matrix.inverted()

        # 5. Calculate the new tail position
        # Note: Edit bone head/tail are in the armature's local space.
        
        # Convert bone head from local to world space
        head_world = armature_matrix @ edit_bone.head
        
        # Calculate the new tail position in world space by adding the
        # directed vector (multiplied by length) to the world head position.
        tail_world_new = head_world + (target_vector * bone_length)
        
        # Convert the new world tail position back to the armature's local space
        tail_local_new = armature_matrix_inverted @ tail_world_new
        
        # 6. Assign the new tail position to the bone
        edit_bone.tail = tail_local_new

        return {'FINISHED'}

class REMOVE_CORRUPTED_PACKED_FILES_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.remove_corrupted_packed_files_vizor"
    bl_label = "remove corrupted packed files"
    bl_description = "remove corrupted packed files"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        # Iterate over all images
        for img in bpy.data.images:
            # Check if the image has no packed files
            if len(img.packed_files) == 0:
                print(f"Deleting corrupted image: {img.name}")
                # Remove the corrupted image
                bpy.data.images.remove(img)
                
        print("Completed cleaning corrupted images.")
        return {'FINISHED'}

class CLEAR_EMMPTY_WEIGHTS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "skin.clear_empty_weights"
    bl_label = "clear empty weights from object"
    bl_description = "clear empty weights from object"
    bl_options = {'REGISTER', 'UNDO'}

    threshold: bpy.props.FloatProperty(default=0, min=0, max=1)

    def find_weights(self, obj):
        maxWeight = {}
        for i in obj.vertex_groups:
            maxWeight[i.index] = 0

        for v in obj.data.vertices:
            for g in v.groups:
                gn = g.group
                w = obj.vertex_groups[gn].weight(v.index)
                if (maxWeight.get(gn) is None or w>maxWeight[gn]):
                    maxWeight[gn] = w
        return maxWeight
    def remove_empty_weights(self, obj):
        maxWeight = self.find_weights(obj)
        # fix bug pointed out by user2859
        ka = []
        ka.extend(maxWeight.keys())
        ka.sort(key=lambda gn: -gn)
        print (ka)
        for gn in ka:
            if maxWeight[gn]<=self.threshold:
                print ("delete %d"%gn)
                obj.vertex_groups.remove(obj.vertex_groups[gn]) # actually remove the group

    def execute(self, context):
        obj = context.active_object
        for obj in [obj for obj in context.selected_objects if obj.type=='MESH']:
            self.remove_empty_weights(obj)
        return {'FINISHED'}

class COPY_NLA_OT_VIZOR(bpy.types.Operator):
    bl_idname = "animation.copy_nla_tracks"
    bl_label = "copy nla tracks from armature"
    bl_description= "copy nla tracks from armature"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'ARMATURE' and len([obj for obj in context.selected_objects if obj.type == 'ARMATURE']) >= 2
    
    def copy_nla_tracks(self, target_rig: bpy.types.Object, source_rig: bpy.types.Object):
        if not source_rig or not source_rig.animation_data:
            print(f"Skipping {source_rig.name}, no animation data found")
            return
        
        if not target_rig.animation_data:
            target_rig.animation_data_create()
            print(f"{target_rig.name} created new animation data")
        
        for track in source_rig.animation_data.nla_tracks:
            target_track_index = target_rig.animation_data.nla_tracks.find(track.name)
            
            if target_track_index == -1:
                new_track = target_rig.animation_data.nla_tracks.new()
                new_track.name = track.name
                new_track.mute = track.mute
            else:
                new_track = target_rig.animation_data.nla_tracks[target_track_index]

            # Store existing strip names to avoid duplicates
            existing_strips = {strip.name for strip in new_track.strips}

            for strip in track.strips:
                if strip.name in existing_strips:
                    print(f"-- {target_rig.name}: Strip '{strip.name}' already exists, skipping")
                    continue  # Avoid duplicate strips
                
                try:
                    new_strip = new_track.strips.new(
                        name=strip.name,
                        start=int(strip.frame_start),
                        action=strip.action
                    )
                    new_strip.action_frame_start = strip.action_frame_start
                    new_strip.action_frame_end = strip.action_frame_end
                    new_strip.blend_type = strip.blend_type
                    new_strip.extrapolation = strip.extrapolation
                    new_strip.frame_end = int(strip.frame_end)
                except RuntimeError as e:
                    print(f"!! {target_rig.name}: Failed to add strip '{strip.name}': {e}")
                    continue  # Skip this strip and proceed to the next one

                print(f"-- {target_rig.name}: Strip '{strip.name}' copied")
            
            print(f"- {target_rig.name}: Track '{track.name}' copied")
        
    
    def execute(self, context):
        # Get active rig as the source
        source_rig = context.active_object

        # Get selected armatures (excluding the source)
        target_rigs = [obj for obj in context.selected_objects if obj.type == 'ARMATURE' and obj != source_rig]

        # Copy NLA tracks to target rigs
        for target in target_rigs:
            self.copy_nla_tracks(target, source_rig)
        return {'FINISHED'}

class COLLECT_WGTS_OT_VIZOR(bpy.types.Operator):
    bl_idname = "rig.collect_wgts"
    bl_label = "collect all wgts in one collection"
    bl_description = "collect all wgts in one collection"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects and bpy.context.selected_objects[0].type == 'ARMATURE'

    def execute(self, context):
        armature = bpy.context.active_object

        # Ensure the selected object is an armature
        if not armature or armature.type != 'ARMATURE':
            print("Please select an armature.")
            return {'CANCELLED'}

        # Get the collections the armature belongs to
        armature_collections = armature.users_collection

        if not armature_collections:
            print(f"Armature '{armature.name}' is not inside any collection.")
            return {'CANCELLED'}

        # Create a new collection for custom shapes
        collection_name = f"wgt-{armature.name}"
        custom_shapes_collection = bpy.data.collections.get(collection_name)

        if not custom_shapes_collection:
            custom_shapes_collection = bpy.data.collections.new(collection_name)

        # Link the new collection to the first collection the armature is in
        parent_collection = armature_collections[0]  # Use the first collection found
        parent_collection.children.link(custom_shapes_collection)

        # Store unique custom shape objects
        custom_shapes = set()

        for bone in armature.pose.bones:
            if bone.custom_shape:
                custom_shapes.add(bone.custom_shape)

        # Move custom shape objects to the new collection
        for shape in custom_shapes:
            for col in shape.users_collection:
                col.objects.unlink(shape)  # Unlink from previous collections
            custom_shapes_collection.objects.link(shape)  # Move to new collection

        print(f"Collected {len(custom_shapes)} custom shapes into '{collection_name}' under '{parent_collection.name}'.")
        return {'FINISHED'}
class APPLY_ARMATURE_OT_VIZOR(bpy.types.Operator):
    bl_idname = "skin.apply_armature_mod"
    bl_label = "apply all armature modifiers"
    bl_description = "apply all armature modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects and bpy.context.selected_objects[0].type == 'MESH'

    def execute(self, context):
        selected_objects = bpy.context.selected_objects
        problem_objects = []

        for obj in selected_objects:
            if obj.type == 'MESH':  # Only process meshes
                armature_modifiers = [mod for mod in obj.modifiers if mod.type == 'ARMATURE']

                if not armature_modifiers:
                    continue  # Skip if no Armature modifier found

                # Ensure object is in Object Mode before applying modifiers
                if obj.mode != 'OBJECT':
                    bpy.ops.object.mode_set(mode='OBJECT')

                bpy.context.view_layer.objects.active = obj  # Set active object

                for mod in armature_modifiers:
                    # Check if the object has shape keys (prevents applying modifier)
                    if obj.data.shape_keys:
                        problem_objects.append((obj.name, "Has shape keys"))
                        continue

                    try:
                        bpy.ops.object.modifier_apply(modifier=mod.name)
                        print(f"✅ Applied '{mod.name}' on '{obj.name}'.")
                    except RuntimeError:
                        problem_objects.append((obj.name, "Unknown error"))

        # Print objects where the modifier couldn't be applied
        if problem_objects:
            print("\n⚠️ The following objects had issues applying Armature modifiers:")
            for obj_name, reason in problem_objects:
                print(f" - {obj_name}: {reason}")
                return {'CANCELLED'}
        return {'FINISHED'}

class FIND_CONCAVE_POLY_OT_VIZOR(bpy.types.Operator):
    bl_idname = "modeling.find_convcave"
    bl_label = "find concave poly"
    bl_description = "find concave poly"
    bl_options = {'REGISTER', 'UNDO'}

    def is_concave(self, poly):
        """Check if a polygon is concave by calculating cross products of edge vectors."""
        normal = poly.normal
        verts = [v for v in poly.verts]  # Fix: No need to index bm.verts
        num_verts = len(verts)
        
        if num_verts < 4:
            return False  # Triangles are always convex

        sign = None
        for i in range(num_verts):
            v1 = verts[i].co - verts[i - 1].co
            v2 = verts[(i + 1) % num_verts].co - verts[i].co
            cross = v1.cross(v2).dot(normal)
            
            if sign is None:
                sign = cross > 0
            elif (cross > 0) != sign:
                return True  # Found a concave angle
        return False

    def select_concave_faces(self):
        """Select concave faces in the active object."""
        obj = bpy.context.object
        if obj is None or obj.type != 'MESH':
            print("Select a mesh object")
            return
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        # Deselect everything first
        for face in bm.faces:
            face.select = False

        # Select concave faces
        concave_found = False
        for face in bm.faces:
            if self.is_concave(face):
                face.select = True
                concave_found = True

        # Update mesh selection
        bmesh.update_edit_mesh(obj.data)

        if concave_found:
            print("Concave faces selected.")
        else:
            print("No concave faces found.")

    @classmethod
    def poll(self, context):
        return bpy.context.selected_objects and bpy.context.object and bpy.context.object.type == 'MESH'

    def execute(self, context):
        bpy.ops.object.mode_set(mode='EDIT')
        self.select_concave_faces()
        return {'FINISHED'}

class SCALE_ANIMATION_OT_VIZOR(bpy.types.Operator):
    """Scale active action after metarig resize and apply scale"""
    bl_idname = "anim.scale_anim"
    bl_label = "Scale Animation"
    bl_description = "Scale Animation"
    bl_options = {'REGISTER', 'UNDO'}

    scale_factor: bpy.props.FloatProperty(
        name="Scale",
        description="By what factor you want to scale the key values",
        default=1.0,
        min=0.0
    )

    @classmethod
    def poll(self, context):
        return context.active_object and context.active_object.type == 'ARMATURE' and context.active_object.animation_data and context.active_object.animation_data.action
    
    def execute(self, context):
        """Scales all location keyframes of an object (or rig) by a given factor."""

        action = context.active_object.animation_data.action

        for fcurve in action.fcurves:
            # Only affect location channels (X, Y, Z)
            if "location" in fcurve.data_path:
                for keyframe_point in fcurve.keyframe_points:
                    keyframe_point.co.y *= self.scale_factor  # keyframe value
                    keyframe_point.handle_left.y *= self.scale_factor
                    keyframe_point.handle_right.y *= self.scale_factor
        return {'FINISHED'}

class CONNECT_BONES_TO_MESH_OT_VIZOR(bpy.types.Operator):
    bl_idname = "rigging.connect_bones_to_mesh"
    bl_label = "connect bones to mesh"
    bl_description= "connects bones to mesh via empties"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return len(context.selected_objects) == 2 and context.active_object and context.active_object.type == 'ARMATURE' and 'MESH' in [obj.type for obj in context.selected_objects if obj != context.active_object]

    def get_selected_bone_names(self, arm_obj):
        return [b.name for b in arm_obj.data.bones if b.select]

    def get_mesh_object(self):
        for obj in bpy.context.selected_objects:
            if obj.type == 'MESH':
                return obj
        return None

    def find_closest_verts(self, mesh_obj, target_location, count=3):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        eval_obj = mesh_obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh()
        eval_verts = eval_mesh.vertices
        world_matrix = mesh_obj.matrix_world

        # Compare original indices, but use evaluated positions
        distances = [
            (i, (world_matrix @ eval_verts[i].co - target_location).length_squared)
            for i in range(len(mesh_obj.data.vertices))  # important: range from ORIGINAL mesh
        ]

        eval_obj.to_mesh_clear()
        closest = sorted(distances, key=lambda x: x[1])[:count]
        return [i for i, _ in closest]

    def parent_to_mesh(self, mesh_obj, empty, vertex_indices):
        """Parent the empty to the mesh using the 3 given vertex indices."""
        # Deselect all and prepare selection
        bpy.ops.object.select_all(action='DESELECT')
        mesh_obj.select_set(True)
        bpy.context.view_layer.objects.active = mesh_obj
        empty.select_set(True)

        # Ensure we're in OBJECT mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Clear previous selection on the mesh vertices
        for v in mesh_obj.data.vertices:
            v.select = False

        # Select the 3 target vertices
        for idx in vertex_indices:
            mesh_obj.data.vertices[idx].select = True

        # Perform vertex triangle parenting
        bpy.ops.object.parent_set(type='VERTEX_TRI')

    def execute(self, context):
        arm_obj = bpy.context.active_object
        if not arm_obj or arm_obj.type != 'ARMATURE':
            print("Active object must be an armature.")
            return {'CANCELED'}

        mesh_obj = self.get_mesh_object()
        if not mesh_obj:
            print("Select a mesh object along with the armature.")
            return {'CANCELED'}

        selected_bones = self.get_selected_bone_names(arm_obj)
        if not selected_bones:
            print("No bones selected.")
            return {'CANCELED'}

        for bone_name in selected_bones:
            bone = arm_obj.data.bones[bone_name]
            pose_bone = arm_obj.pose.bones[bone_name]
            bone_world_matrix = arm_obj.matrix_world @ bone.matrix_local

            # Create empty aligned to bone
            empty = bpy.data.objects.new(f"Empty_{bone_name}", None)
            bpy.context.collection.objects.link(empty)
            empty.matrix_world = bone_world_matrix

            # Add constraints to make bone follow the empty
            con_loc = pose_bone.constraints.new('COPY_LOCATION')
            con_loc.target = empty
            con_rot = pose_bone.constraints.new('COPY_ROTATION')
            con_rot.target = empty

            # Find 3 closest vertices in the mesh
            closest_verts = self.find_closest_verts(mesh_obj, empty.location, 3)
            if len(closest_verts) < 3:
                print(f"Not enough vertices found for bone {bone_name}")
                continue

            # Parent the empty to those 3 vertices
            self.parent_to_mesh(mesh_obj, empty, closest_verts)

        print("Done: Empties created, bones constrained, and empties vertex-triangle parented.")
        return {'FINISHED'}

class OBJECT_OT_surface_deform_setup(bpy.types.Operator):
    """Add/Update Surface Deform modifier and bind"""
    bl_idname = "object.surface_deform_setup"
    bl_label = "Setup Surface Deform"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.active_object
        selected = context.selected_objects

        # Require at least two objects: target and deform mesh
        if len(selected) < 2 or active.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh target and another object to deform.")
            return {'CANCELLED'}

        # Target = active object, Deforming object = first other mesh in selection
        target_obj = active
        deform_objs = (obj for obj in selected if obj != active and obj.type == 'MESH')
        for deform_obj in deform_objs:
            if not deform_obj:
                self.report({'ERROR'}, "No deform mesh found in selection.")
                return {'CANCELLED'}

            # Find or create Surface Deform modifier
            sdef_mod = None
            for mod in deform_obj.modifiers:
                if mod.type == 'SURFACE_DEFORM':
                    sdef_mod = mod
                    break

            if not sdef_mod:
                sdef_mod = deform_obj.modifiers.new(name="SurfaceDeform", type='SURFACE_DEFORM')

            # Move modifier to top of stack
            while deform_obj.modifiers[0] != sdef_mod:
                bpy.context.view_layer.objects.active = deform_obj
                bpy.ops.object.modifier_move_up(modifier=sdef_mod.name)

            # Set target object
            sdef_mod.target = target_obj

            # Make sure deform_obj is active for binding
            bpy.context.view_layer.objects.active = deform_obj

            # Bind or Rebind
            if not sdef_mod.is_bound:
                bpy.ops.object.surfacedeform_bind(modifier=sdef_mod.name)
            else:
                bpy.ops.object.surfacedeform_bind(modifier=sdef_mod.name)
                bpy.ops.object.surfacedeform_bind(modifier=sdef_mod.name)

        self.report({'INFO'}, f"Surface Deform set up on {deform_obj.name} with target {target_obj.name}")
        return {'FINISHED'}

class TRANSFER_WEIGHTS_TO_LATTICE_OT_VIZOR(bpy.types.Operator):
    bl_idname = "rigging.mesh_to_lattice_weights_transfer"
    bl_label = "transfer mesh weights to lattice"
    bl_description= "transfer weights from mesh to lattice"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return len(context.selected_objects) == 2 and context.active_object and context.active_object.type == 'LATTICE' and 'MESH' in [obj.type for obj in context.selected_objects if obj != context.active_object]
    
    def transfer_vertex_group_weights_to_lattice(self, lattice_obj, mesh_obj):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        mesh_eval = mesh_obj.evaluated_get(depsgraph)
        mesh_data = mesh_eval.to_mesh()

        # Step 1: Copy vertex groups from mesh to lattice
        lattice_obj.vertex_groups.clear()
        for vg in mesh_obj.vertex_groups:
            lattice_obj.vertex_groups.new(name=vg.name)

        # Step 2: Build KDTree for mesh vertices (in world space)
        size = len(mesh_data.vertices)
        kd = kdtree.KDTree(size)

        vertex_co_world = []
        for i, v in enumerate(mesh_data.vertices):
            co_world = mesh_obj.matrix_world @ v.co
            vertex_co_world.append((v, co_world))
            kd.insert(co_world, i)

        kd.balance()

        # Step 3: Transfer weights
        for i, point in enumerate(lattice_obj.data.points):
            point_world = lattice_obj.matrix_world @ point.co
            _, index, _ = kd.find(point_world)
            closest_vertex, _ = vertex_co_world[index]

            for vg_elem in closest_vertex.groups:
                mesh_vg_name = mesh_obj.vertex_groups[vg_elem.group].name
                lattice_vg = lattice_obj.vertex_groups.get(mesh_vg_name)
                if lattice_vg:
                    lattice_vg.add([i], vg_elem.weight, 'REPLACE')

        # Clean up
        mesh_eval.to_mesh_clear()
        print("✅ Vertex group weights transferred to lattice (optimized).")

    def execute(self, context):
        # --- Usage ---
        lattice = None
        mesh = None

        for obj in bpy.context.selected_objects:
            if obj.type == 'LATTICE':
                lattice = obj
            elif obj.type == 'MESH':
                mesh = obj

        if lattice and mesh:
            self.transfer_vertex_group_weights_to_lattice(lattice, mesh)
            return {'FINISHED'}
        else:
            print("⚠️ Select one mesh and one lattice.")
            return {'CANCELLED'}

class CLEAN_UP_SCENE_OT_VIZOR(bpy.types.Operator):
    bl_idname = "post.clean_up_scene"
    bl_label = "clean up scene from annatation and markers"
    bl_description= "clean up scene from annatation and markers"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(self, context):
        return context.mode == 'OBJECT'
    def execute(self, context):
        import bpy

        # --- Remove all annotations ---
        for annotation in bpy.data.grease_pencils:
            if 'Annotations' in annotation.name:
                bpy.data.grease_pencils.remove(annotation)

        # --- Remove all timeline markers ---
        bpy.context.scene.timeline_markers.clear()

        print("All annotations and timeline markers removed.")

        return {'FINISHED'}

class ResetIKStretch_OT_VIZOR(bpy.types.Operator):
    """Remove IK_Stretch curves from NLA actions, set to 1.0, and key at frame 0"""
    bl_idname = "pose.reset_ik_stretch_nla"
    bl_label = "Reset IK Stretch in NLA Actions"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only run if an armature is active and we are in Pose Mode
        return (context.active_object and 
                context.active_object.type == 'ARMATURE' and 
                context.mode == 'POSE')

    def execute(self, context):
        obj = context.active_object
        sel_bones = context.selected_pose_bones
        prop_name = "IK_Stretch"

        if not sel_bones:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}

        if not obj.animation_data or not obj.animation_data.nla_tracks:
            self.report({'WARNING'}, "Armature has no NLA tracks/actions")
            return {'CANCELLED'}

        # 1. Identify all unique actions used in NLA tracks
        nla_actions = set()
        for track in obj.animation_data.nla_tracks:
            for strip in track.strips:
                if strip.action:
                    nla_actions.add(strip.action)

        if not nla_actions:
            self.report({'INFO'}, "No actions found inside NLA strips")
            return {'FINISHED'}

        curves_modified = 0

        # 2. Iterate through actions and selected bones
        for action in nla_actions:
            # 1. Get the identifier for the active armature slot
            slot = action.slots.active
            if not slot:
                continue
            slot_id = slot.identifier

            # 2. Get the Layer and Strip
            if not action.layers:
                action.layers.new(name="Base Layer")
            layer = action.layers[0]

            if not layer.strips:
                layer.strips.new(name="Base Strip", type='KEYFRAME')
            strip = layer.strips[0]

            # 3. Find the ChannelBag for this specific Slot manually
            bag = None
            for b in strip.channelbags:
                if b.slot_identifier == slot_id:
                    bag = b
                    break
            
            # 4. If the bag doesn't exist, create it and assign the identifier
            if not bag:
                bag = strip.channelbags.new()
                bag.slot_identifier = slot_id

            for pbone in sel_bones:
                pbone[prop_name] = 1.0
                data_path = f'pose.bones["{pbone.name}"]["{prop_name}"]'

                # 5. Remove existing F-Curve from this bag
                # fcurves.find() usually works inside the bag
                fcurve = bag.fcurves.find(data_path)
                if fcurve:
                    bag.fcurves.remove(fcurve)

                # 6. Handle Groups (Groups inside bags DO support .get())
                bone_group = bag.groups.get(pbone.name)
                if bone_group is None:
                    bone_group = bag.groups.new(name=pbone.name)

                # 7. Create the new F-Curve
                new_fcurve = bag.fcurves.new(data_path=data_path)
                new_fcurve.group = bone_group
                
                # Insert the keyframe
                new_fcurve.keyframe_points.insert(frame=0, value=1.0)
                curves_modified += 1

        self.report({'INFO'}, f"Processed {curves_modified} channels. Groups created/verified.")
        return {'FINISHED'}

class POSE_OT_MaintainVolumeAnimation_OR_VIZOR(bpy.types.Operator):
    """Maintain bone volume based on primary axis scale keyframes"""
    bl_idname = "pose.maintain_volume_keys"
    bl_label = "Maintain Volume (Keyframes)"
    bl_options = {'REGISTER', 'UNDO'}

    primary_axis: bpy.props.EnumProperty(
        name="Primary Axis",
        description="The axis that drives the scale animation",
        items=[
            ('0', "X", "Use X as primary axis"),
            ('1', "Y", "Use Y as primary axis"),
            ('2', "Z", "Use Z as primary axis"),
        ],
        default='1'
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'POSE' and context.active_object and context.active_object.type == 'ARMATURE'

    def execute(self, context):
        obj = context.active_object
        selected_bones = context.selected_pose_bones
        
        if not selected_bones:
            self.report({'WARNING'}, "No bones selected")
            return {'CANCELLED'}

        if not obj.animation_data or not obj.animation_data.action:
            self.report({'WARNING'}, "No animation data/action found on armature")
            return {'CANCELLED'}

        action = obj.animation_data.action
        primary_idx = int(self.primary_axis)
        # Determine secondary axes
        secondary_indices = [i for i in range(3) if i != primary_idx]

        for bone in selected_bones:
            data_path = f'pose.bones["{bone.name}"].scale'
            
            # 1. Find the primary F-Curve
            primary_fcurve = next((fc for fc in action.fcurves if fc.data_path == data_path and fc.array_index == primary_idx), None)
            
            if not primary_fcurve:
                self.report({'INFO'}, f"No scale keyframes for bone {bone.name} on selected axis. Skipping.")
                continue

            # 2. Clear existing keyframes on secondary scale channels
            for s_idx in secondary_indices:
                fc_to_remove = next((fc for fc in action.fcurves if fc.data_path == data_path and fc.array_index == s_idx), None)
                if fc_to_remove:
                    action.fcurves.remove(fc_to_remove)

            # 3. Iterate through primary keyframes and calculate secondary values
            # We collect frame and value pairs first to avoid issues during insertion
            keys_to_add = []
            for kp in primary_fcurve.keyframe_points:
                frame = kp.co[0]
                primary_val = kp.co[1]
                
                # Formula: Primary * Sec * Sec = 1  => Sec = sqrt(1 / Primary)
                # Handle division by zero or negative scales
                if primary_val <= 0:
                    secondary_val = 1.0 
                else:
                    secondary_val = math.sqrt(1.0 / primary_val)
                
                keys_to_add.append((frame, secondary_val))

            # 4. Apply new keyframes
            for frame, val in keys_to_add:
                for s_idx in secondary_indices:
                    bone.scale[s_idx] = val
                    bone.keyframe_insert(data_path="scale", index=s_idx, frame=frame)

        self.report({'INFO'}, "Volume maintained for selected bones.")
        return {'FINISHED'}

class MESH_RemoveNonDeformVGroups_OT_VIZOR(bpy.types.Operator):
    """Remove all vertex groups not associated with a deforming bone in the armature(s)"""
    bl_idname = "mesh.remove_non_deform_vgroups"
    bl_label = "Remove Non-Deform Vertex Groups"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if not context.selected_objects:
            return False
        
        # Check if at least one selected mesh has an armature modifier
        for obj in context.selected_objects:
            if obj.type == 'MESH':
                if any(m.type == 'ARMATURE' and m.object for m in obj.modifiers):
                    return True
        return False

    def execute(self, context):
        # Filter selection to meshes only
        selected_meshes = [obj for obj in context.selected_objects if obj.type == 'MESH']
        
        total_removed_count = 0
        processed_objects_count = 0

        for obj in selected_meshes:
            # 1. Find all armature modifiers for THIS specific object
            arm_modifiers = [m for m in obj.modifiers if m.type == 'ARMATURE' and m.object]
            
            # Skip this object if it has no armatures assigned
            if not arm_modifiers:
                continue
                
            # 2. Build a set of all valid deform bone names from all attached armatures
            deform_bone_names = set()
            for mod in arm_modifiers:
                arm_obj = mod.object
                for bone in arm_obj.data.bones:
                    if bone.use_deform:
                        deform_bone_names.add(bone.name)

            # 3. Identify vertex groups on this mesh that are NOT in the deform set
            vgroups_to_remove = [vg for vg in obj.vertex_groups if vg.name not in deform_bone_names]

            # 4. Remove the groups
            if vgroups_to_remove:
                processed_objects_count += 1
                for vg in vgroups_to_remove:
                    obj.vertex_groups.remove(vg)
                    total_removed_count += 1
            
        # Final report
        self.report(
            {'INFO'}, 
            f"Processed {processed_objects_count} objects. Removed {total_removed_count} vertex groups."
        )
        
        return {'FINISHED'}

classes = (
            RESET_STRETCH_OT_VIZOR,
            REMOVE_CORRUPTED_PACKED_FILES_OT_VIZOR,
            RESET_TRANSFORM_OT_VIZOR,
            MOVE_ARMATURE_UP_OT_VIZOR,
            SELECT_DEF_BONES_OT_VIZOR,
            SELECT_CTRL_BONES_OT_VIZOR,
            SELECT_VGROUP_BONES_OT_VIZOR,
            COPY_BONES_POSITION_OT_VIZOR,
            CLEAR_MISSING_CHANNELS_OT_VIZOR,
            MIRROR_WEIGHTS_OT_VIZOR,
            OFFSET_KEYFRAMES_OT_VIZOR,
            CLEAR_VGROUPS_OT_VIZOR,
            COPY_SHAPE_KEYS_OT_VIZOR,
            CLEAR_EMMPTY_WEIGHTS_OT_VIZOR,
            COLLECT_WGTS_OT_VIZOR,
            APPLY_ARMATURE_OT_VIZOR,
            FIND_CONCAVE_POLY_OT_VIZOR,
            COPY_NLA_OT_VIZOR,
            SCALE_ANIMATION_OT_VIZOR,
            CONNECT_BONES_TO_MESH_OT_VIZOR,
            TRANSFER_WEIGHTS_TO_LATTICE_OT_VIZOR,
            OBJECT_OT_surface_deform_setup,
            CLEAN_UP_SCENE_OT_VIZOR,
            ALIGN_TO_WORLD_AXIS_OT_VIZOR,
            ANIM_OT_clean_bone_channels_VIZOR,
            ResetIKStretch_OT_VIZOR,
            POSE_OT_MaintainVolumeAnimation_OR_VIZOR,
            POSE_SwapAnimationChannels_OT_VIZOR,
            IMAGE_downscale_all_OT_VIZOR,
            NLA_SetPreviewRangeToStrips_OT_VIZOR,
            MESH_RemoveNonDeformVGroups_OT_VIZOR,
            VIZOR_ANIMATION_PT_VIZOR,
        )
        
def register():
    for my_class in classes:
        bpy.utils.register_class(my_class)
        
        
def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)
            
if __name__ == '__main__':
    register()