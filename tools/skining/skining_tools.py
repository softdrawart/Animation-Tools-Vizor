bl_info = {
    "name": "Proximity Weight Transfer",
    "author": "AI Assistant",
    "version": (1, 1),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Skinning",
    "description": "Transfers vertex weights from a selected mesh or nearby unselected vertices to selected vertices.",
    "warning": "",
    "doc_url": "",
    "category": "Mesh",
}

import bpy
import bmesh
from mathutils.kdtree import KDTree


class MESH_OT_proximity_weight_transfer(bpy.types.Operator):
    """Transfer weights from a source object or unselected closest vertices to selected vertices"""
    bl_idname = "mesh.proximity_weight_transfer"
    bl_label = "Transfer Nearby Weights"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        # Only allow execution if we are actively editing a mesh
        return context.edit_object is not None and context.edit_object.type == 'MESH'

    def execute(self, context):
        obj = context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)
        scene = context.scene

        distance_limit = scene.weight_transfer_threshold
        source_obj = scene.weight_source_object

        weight_layer = bm.verts.layers.deform.active
        if not weight_layer:
            weight_layer = bm.verts.layers.deform.new()

        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts:
            self.report({'WARNING'}, "No target vertices selected!")
            return {'CANCELLED'}

        transferred_count = 0

        # --- MODE 1: EXTERNAL OBJECT TRANSFER ---
        if source_obj and source_obj != obj:
            if source_obj.type != 'MESH':
                self.report({'ERROR'}, "Source object must be a Mesh!")
                return {'CANCELLED'}
            
            # Fetch transformation matrices to convert local to world space
            active_matrix = obj.matrix_world
            source_matrix = source_obj.matrix_world
            
            # Map source vertex group indices to target vertex group indices by name
            source_vgs = source_obj.vertex_groups
            target_vgs = obj.vertex_groups
            vg_map = {}
            for svg in source_vgs:
                tvg = target_vgs.get(svg.name)
                # Create the vertex group on the target if it doesn't exist
                if not tvg:
                    tvg = obj.vertex_groups.new(name=svg.name)
                vg_map[svg.index] = tvg.index

            # Read source mesh data
            bm_source = bmesh.new()
            bm_source.from_mesh(source_obj.data)
            source_weight_layer = bm_source.verts.layers.deform.active
            
            if not source_weight_layer:
                bm_source.free()
                self.report({'WARNING'}, "Source object has no vertex weights!")
                return {'CANCELLED'}

            # Build KDTree with source coordinates translated to world space
            tree = KDTree(len(bm_source.verts))
            for i, v in enumerate(bm_source.verts):
                tree.insert(source_matrix @ v.co, i)
            tree.balance()
            
            # --- ADD THIS LINE HERE ---
            bm_source.verts.ensure_lookup_table()
            
            # Transfer loop
            for v_target in selected_verts:
                # Convert target local to world space for the lookup
                world_co = active_matrix @ v_target.co
                co, index, dist = tree.find(world_co)
                
                if dist <= distance_limit:
                    v_source = bm_source.verts[index]
                    v_target[weight_layer].clear()
                    
                    for group_id, weight in v_source[source_weight_layer].items():
                        mapped_id = vg_map.get(group_id)
                        if mapped_id is not None:
                            v_target[weight_layer][mapped_id] = weight
                    transferred_count += 1
            
            bm_source.free()
            
        # --- MODE 2: INTERNAL FALLBACK TRANSFER ---
        else:
            if source_obj == obj:
                self.report({'WARNING'}, "Source object matches active. Falling back to internal unselected vertices.")

            unselected_verts = [v for v in bm.verts if not v.select]
            
            if not unselected_verts:
                self.report({'WARNING'}, "No source (unselected) vertices found to copy from!")
                return {'CANCELLED'}

            # KDTree in local space (since both are identical mesh data)
            tree = KDTree(len(unselected_verts))
            for i, v in enumerate(unselected_verts):
                tree.insert(v.co, i)
            tree.balance()

            for v_target in selected_verts:
                co, index, dist = tree.find(v_target.co)
                
                if dist <= distance_limit:
                    v_source = unselected_verts[index]
                    v_target[weight_layer].clear()
                    
                    for group_id, weight in v_source[weight_layer].items():
                        v_target[weight_layer][group_id] = weight
                    transferred_count += 1

        bmesh.update_edit_mesh(me)
        self.report({'INFO'}, f"Successfully transferred weights for {transferred_count} vertices.")
        return {'FINISHED'}


class VIEW3D_PT_proximity_weight_panel(bpy.types.Panel):
    """Creates a dedicated UI Sidebar panel for managing the transfer tools"""
    bl_label = "Proximity Weight Transfer"
    bl_idname = "VIEW3D_PT_proximity_weight_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Skinning'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        col.label(text="Transfer Settings:")
        
        # Pointer property naturally renders with an eyedropper icon in Blender's UI
        col.prop(scene, "weight_source_object", text="Source Object")
        col.prop(scene, "weight_transfer_threshold", text="Max Proximity")
        
        layout.separator()
        layout.operator("mesh.proximity_weight_transfer", icon='MOD_VERTEX_WEIGHT')


classes = (
    MESH_OT_proximity_weight_transfer,
    VIEW3D_PT_proximity_weight_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.weight_transfer_threshold = bpy.props.FloatProperty(
        name="Threshold Distance",
        description="Maximum distance allowed between source and target vertices to execute a transfer",
        default=0.05,
        min=0.001,
        max=5.0,
        precision=4,
        subtype='DISTANCE'
    )
    
    bpy.types.Scene.weight_source_object = bpy.props.PointerProperty(
        type=bpy.types.Object,
        name="Source Mesh",
        description="Select source mesh for weight transfer (leave empty for same-mesh transfer)"
    )

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        
    del bpy.types.Scene.weight_transfer_threshold
    del bpy.types.Scene.weight_source_object

if __name__ == "__main__":
    register()