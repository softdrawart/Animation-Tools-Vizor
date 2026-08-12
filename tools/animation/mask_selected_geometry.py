
import bpy

def get_related_meshes(armature):
    meshes = set()
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == armature:
                    meshes.add(obj)
                    break
            if obj.parent == armature:
                meshes.add(obj)
    return list(meshes)

class ANIM_OT_ModifySoloMask(bpy.types.Operator):
    """Add or Remove bones from the existing Solo Mask"""
    bl_idname = "anim.modify_solo_mask"
    bl_label = "Modify Solo Mask"
    bl_options = {'REGISTER', 'UNDO'}
    
    action: bpy.props.EnumProperty(items=[('ADD', 'Add', ''), ('REMOVE', 'Remove', '')])

    def execute(self, context):
        armature = context.active_object
        selected_bones = [b.name for b in context.selected_pose_bones]
        if not selected_bones: return {'CANCELLED'}

        for obj in get_related_meshes(armature):
            mask_group = obj.vertex_groups.get("Solo_Mask")
            if not mask_group: continue # Can only modify if it already exists

            # Get indices for selected bones
            bone_indices = [obj.vertex_groups[b].index for b in selected_bones if b in obj.vertex_groups]
            
            # Identify vertices to change
            target_indices = []
            for vert in obj.data.vertices:
                if any(g.group in bone_indices and g.weight > 0.001 for g in vert.groups):
                    target_indices.append(vert.index)
            
            # Handle Parenting check
            if obj.parent_type == 'BONE' and obj.parent_bone in selected_bones:
                target_indices = [v.index for v in obj.data.vertices]

            if target_indices:
                mask_group.add(target_indices, 1.0, 'ADD' if self.action == 'ADD' else 'SUBTRACT')
        
        return {'FINISHED'}

class ANIM_OT_SoloBoneGeometry(bpy.types.Operator):
    """Solo geometry (Reset and set to selection)"""
    bl_idname = "anim.solo_bone_geometry"
    bl_label = "Solo Selected Bone Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        armature = context.active_object
        selected_bone_names = [b.name for b in context.selected_pose_bones]
        
        for obj in get_related_meshes(armature):
            mask_group = obj.vertex_groups.get("Solo_Mask")
            if mask_group: obj.vertex_groups.remove(mask_group)
            mask_group = obj.vertex_groups.new(name="Solo_Mask")

            bone_group_indices = [obj.vertex_groups[b].index for b in selected_bone_names if b in obj.vertex_groups]
            
            for vert in obj.data.vertices:
                if any(g.group in bone_group_indices and g.weight > 0.001 for g in vert.groups):
                    mask_group.add([vert.index], 1.0, 'REPLACE')

            if obj.parent_type == 'BONE' and obj.parent_bone in selected_bone_names:
                mask_group.add([v.index for v in obj.data.vertices], 1.0, 'REPLACE')

            if not obj.modifiers.get("Solo_Mask_Modifier"):
                mod = obj.modifiers.new(name="Solo_Mask_Modifier", type='MASK')
                mod.vertex_group = "Solo_Mask"
        return {'FINISHED'}

class ANIM_OT_RemoveSoloMask(bpy.types.Operator):
    bl_idname = "anim.remove_solo_mask"
    bl_label = "Remove Mask & Cleanup"
    def execute(self, context):
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                if obj.modifiers.get("Solo_Mask_Modifier"): obj.modifiers.remove(obj.modifiers["Solo_Mask_Modifier"])
                if obj.vertex_groups.get("Solo_Mask"): obj.vertex_groups.remove(obj.vertex_groups["Solo_Mask"])
        return {'FINISHED'}

class VIEW3D_PT_BoneSoloPanel(bpy.types.Panel):
    bl_label = "Bone Geometry Solo"
    bl_idname = "VIEW3D_PT_bone_solo"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Animation'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.operator("anim.solo_bone_geometry", text="Solo Selected", icon='HIDE_OFF')
        col.separator()
        row = col.row(align=True)
        op_add = row.operator("anim.modify_solo_mask", text="Add to Solo", icon='ADD')
        op_add.action = 'ADD'
        op_sub = row.operator("anim.modify_solo_mask", text="Remove from Solo", icon='REMOVE')
        op_sub.action = 'REMOVE'
        col.separator()
        col.operator("anim.remove_solo_mask", text="Cleanup", icon='TRASH')

classes = (
    ANIM_OT_ModifySoloMask,
    ANIM_OT_SoloBoneGeometry,
    ANIM_OT_RemoveSoloMask,
    VIEW3D_PT_BoneSoloPanel
)

def register():
    for my_class in classes:
        bpy.utils.register_class(my_class)

def unregister():
    for my_class in reversed(classes):
        bpy.utils.unregister_class(my_class)

if __name__ == "__main__":
    register()