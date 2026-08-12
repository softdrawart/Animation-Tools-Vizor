
import bpy
from mathutils import Matrix, Vector


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

PRIMITIVE_ITEMS = [
    ("SPHERE", "UV Sphere", "Place a UV Sphere"),
    ("ICOSPHERE", "Ico Sphere", "Place an Ico Sphere"),
    ("CUBE", "Cube", "Place a Cube"),
    ("CYLINDER", "Cylinder", "Place a Cylinder"),
    ("CONE", "Cone", "Place a Cone"),
]


def bone_world_matrix(obj, pbone):
    """World matrix with origin at the bone head, aligned to the bone."""
    return obj.matrix_world @ pbone.matrix


def parent_to_bone_with_offset(child, arm_obj, bone_name):
    """Parent child Object to armature bone keeping current world transform."""
    child.parent = arm_obj
    child.parent_type = 'BONE'
    child.parent_bone = bone_name
    # Compute parent inverse so current world transform is preserved
    bone_mx_world = arm_obj.matrix_world @ arm_obj.pose.bones[bone_name].matrix
    vec = (arm_obj.pose.bones[bone_name].head - arm_obj.pose.bones[bone_name].tail) * .5
    child.matrix_parent_inverse = bone_mx_world.inverted() @ Matrix.Translation(vec)


# -------------------------------------------------------------------
# Operator
# -------------------------------------------------------------------

class BPP_OT_place(bpy.types.Operator):
    bl_idname = "bpp.place"
    bl_label = "Create Primitive(s) on Selected Bones"
    bl_options = {'REGISTER', 'UNDO'}

    primitive: bpy.props.EnumProperty(
        name="Primitive",
        items=PRIMITIVE_ITEMS,
        description="Primitive to create for each selected pose bone",
        default="SPHERE",
    )

    def invoke(self, context, event):
        return self.execute(context)

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'ARMATURE':
            self.report({'ERROR'}, "Select an Armature and enter Pose Mode.")
            return {'CANCELLED'}
        if context.mode != 'POSE':
            self.report({'ERROR'}, "Enter Pose Mode and select one or more bones.")
            return {'CANCELLED'}

        bones = context.selected_pose_bones or []
        if not bones:
            self.report({'ERROR'}, "No pose bones selected.")
            return {'CANCELLED'}

        created = []
        for pbone in bones:
            length = max(pbone.length, 1e-6)
            name = f"{pbone.name}_{self.primitive.lower()}"

            # Add primitive roughly matching the bone length
            if self.primitive == 'SPHERE':
                bpy.ops.mesh.primitive_uv_sphere_add(radius=length * 0.5)
            elif self.primitive == 'ICOSPHERE':
                bpy.ops.mesh.primitive_ico_sphere_add(radius=length * 0.5, subdivisions=2)
            elif self.primitive == 'CUBE':
                bpy.ops.mesh.primitive_cube_add(size=length)
            elif self.primitive == 'CYLINDER':
                bpy.ops.mesh.primitive_cylinder_add(radius=length * 0.15, depth=length)
            elif self.primitive == 'CONE':
                bpy.ops.mesh.primitive_cone_add(radius1=length * 0.2, radius2=0.0, depth=length)
            else:
                self.report({'ERROR'}, f"Unsupported primitive: {self.primitive}")
                continue

            new_obj = context.active_object
            new_obj.name = name

            # Align to bone
            new_obj.matrix_world = bone_world_matrix(obj, pbone)

            # Parent with offset to the bone
            parent_to_bone_with_offset(new_obj, obj, pbone.name)

            created.append(new_obj.name)
        
        
        # Restore armature as active and switch back to Pose Mode
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='POSE')

        # Reselect the original bones
        for pbone in obj.pose.bones:
            pbone.bone.select = False
        for pbone in bones:
            pbone.bone.select = True

        self.report({'INFO'}, f"Created {len(created)} object(s): {', '.join(created)}")
        return {'FINISHED'}


# -------------------------------------------------------------------
# UI Panel
# -------------------------------------------------------------------

class BPP_PT_panel(bpy.types.Panel):
    bl_label = "Bone Primitives"
    bl_idname = "BPP_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Bone Primitives'

    def draw(self, context):
        layout = self.layout
        col = layout.column(align=True)
        col.label(text="Place on Selected Bones")
        row = col.row()
        row.prop(context.scene, 'bpp_primitive', text="Primitive")
        op = col.operator('bpp.place', text="Create Primitive(s)", icon='MESH_MONKEY')
        op.primitive = context.scene.bpp_primitive


# -------------------------------------------------------------------
# Properties
# -------------------------------------------------------------------

def register_props():
    bpy.types.Scene.bpp_primitive = bpy.props.EnumProperty(
        name="Primitive",
        items=PRIMITIVE_ITEMS,
        description="Primitive to create for each selected pose bone",
        default="SPHERE",
    )


def unregister_props():
    if hasattr(bpy.types.Scene, 'bpp_primitive'):
        del bpy.types.Scene.bpp_primitive


# -------------------------------------------------------------------
# Registration
# -------------------------------------------------------------------

classes = (
    BPP_OT_place,
    BPP_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_props()


def unregister():
    unregister_props()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
