import bpy
import os

bl_info = {
    "name": "Turntable Render",
    "author": "Hallway, BeyondDev (Tyler Walker)",
    "version": (1, 7),
    "blender": (3, 6, 0),
    "category": "Render",
    "location": "View3D > UI > Tools",
    "description": "Render Out Turntable Images with Desired Render Passes",
    "warning": "",
    "wiki_url": "",
}

class TurntableRenderProperties(bpy.types.PropertyGroup):
    num_images: bpy.props.IntProperty(name="Number of Images", default=8, min=1)
    prefix: bpy.props.StringProperty(name="Prefix", default="Turntable")
    directory: bpy.props.StringProperty(name="Directory", default="//images", subtype='DIR_PATH')  # Default changed to "images"
    progress: bpy.props.FloatProperty(name="Progress", default=0.0)
    render_pass: bpy.props.EnumProperty(
        name="Render Pass",
        items=[
            ('ALL', 'All', ''),
            ('COMBINED', 'Combined', ''),
            ('DEPTH', 'Depth', ''),
            ('NORMAL', 'Normal', ''),
            ('ALPHA', 'Alpha', '')  # Added 'ALPHA'
        ],
        default='COMBINED'
    )

class TurntableRenderPanel(bpy.types.Panel):
    bl_label = "Turntable Render"
    bl_idname = "PT_TurntableRenderPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Tool'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        turntable_props = scene.turntable_props
        view = context.space_data

        layout.prop(turntable_props, "num_images")
        row = layout.row()
        row.label(text=f"Degrees per Stop: {360 / turntable_props.num_images:.2f}", icon='NONE')
        row.alignment = 'CENTER'
        
        # Separator
        layout.separator()
        # Camera selection and lock-to-view
        row = layout.row(align=True)
        row.label(text='Select Camera')
        row = layout.row(align=True)
        row.scale_y = 1.1
        row.prop(scene, "camera")
        row = layout.row(align=True)
        row.scale_y = 1.1
        row.prop(view, "lock_camera", text="Camera to View")

        layout.prop(turntable_props, "prefix")
        layout.prop(turntable_props, "directory")
        layout.prop(turntable_props, "render_pass")
        layout.operator("object.turntable_render")

        if turntable_props.progress > 0 and turntable_props.progress < 100:
            # Percentage complete readout
            layout.label(text=f"Percentage Complete: {turntable_props.progress:.2f}%")


class TurntableRenderOperator(bpy.types.Operator):
    bl_label = "Render Turntable"
    bl_idname = "object.turntable_render"

    def execute(self, context):
        scene = context.scene
        turntable_props = scene.turntable_props

        # Render settings
        passes_to_render = [str(turntable_props.render_pass)] if turntable_props.render_pass != 'ALL' else ['COMBINED', 'DEPTH', 'NORMAL', 'ALPHA']

        # Save original settings
        original_file_format = scene.render.image_settings.file_format
        original_filepath = scene.render.filepath

        # Set new settings
        scene.render.image_settings.file_format = 'PNG'

        # Create directory for images
        dir_path = bpy.path.abspath(turntable_props.directory)
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

        # Save original settings
        original_pass_z = scene.view_layers["0: Combined"].use_pass_z
        original_pass_normal = scene.view_layers["0: Combined"].use_pass_normal
        original_camera_parent = context.scene.camera.parent

        # Create circle and parent camera to it
        bpy.ops.mesh.primitive_circle_add(radius=1, location=(0, 0, 0))
        circle = bpy.context.object
        context.scene.camera.parent = circle

        # Compositor settings
        bpy.context.scene.use_nodes = True
        tree = bpy.context.scene.node_tree

        # Check if nodes already exist, otherwise create them
        render_layers_node = next((node for node in tree.nodes if node.name.startswith('Render Layers')), None)
        if render_layers_node is None:
            render_layers_node = tree.nodes.new('CompositorNodeRLayers')

        composite_node = next((node for node in tree.nodes if node.name.startswith('Composite')), None)
        if composite_node is None:
            composite_node = tree.nodes.new('CompositorNodeComposite')

        # Store original connections
        original_links = [(link.from_socket, link.to_socket) for link in tree.links]

        # List to store created nodes
        created_nodes = []

        completed_renders = 0
        total_renders = turntable_props.num_images * len(passes_to_render)

        for render_pass in passes_to_render:
            # Clear previous connections
            for link in tree.links:
                tree.links.remove(link)

            if render_pass == 'DEPTH':
                scene.view_layers["0: Combined"].use_pass_z = True
                normalize_node = next((node for node in tree.nodes if node.name.startswith('Normalize')), None)
                if normalize_node is None:
                    normalize_node = tree.nodes.new('CompositorNodeNormalize')
                created_nodes.append(normalize_node.name)
                subtract_node = tree.nodes.get('Subtract') or tree.nodes.new('CompositorNodeMath')
                subtract_node.operation = 'SUBTRACT'
                subtract_node.inputs[0].default_value = 1.0
                tree.links.new(render_layers_node.outputs['Depth'], normalize_node.inputs[0])
                tree.links.new(normalize_node.outputs[0], subtract_node.inputs[1])
                tree.links.new(subtract_node.outputs[0], composite_node.inputs['Image'])
                created_nodes.extend([normalize_node, subtract_node])
            elif render_pass == 'NORMAL':
                scene.view_layers["0: Combined"].use_pass_normal = True
                tree.links.new(render_layers_node.outputs['Normal'], composite_node.inputs['Image'])
            elif render_pass == 'ALPHA':
                tree.links.new(render_layers_node.outputs['Alpha'], composite_node.inputs['Image'])
            elif render_pass == 'COMBINED':
                tree.links.new(render_layers_node.outputs['Image'], composite_node.inputs['Image'])

            for i in range(turntable_props.num_images):
                angle = i * (360 / turntable_props.num_images)
                circle.rotation_euler.z = angle * (3.14159 / 180)

                # Update all open image editors and N-panels
                for window in bpy.context.window_manager.windows:
                    for area in window.screen.areas:
                        if area.type == 'IMAGE_EDITOR':
                            area.tag_redraw()
                        elif area.type == 'VIEW_3D':
                            for region in area.regions:
                                if region.type == 'UI':  # N-panel is the UI region in VIEW_3D
                                    region.tag_redraw()
                
                # Update the viewport and render preview
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                bpy.context.view_layer.update()

                # Update completed renders
                completed_renders += 1
                percentage_complete = (completed_renders / total_renders) * 100
                bpy.context.window_manager.progress_update(int(percentage_complete))
                turntable_props.progress = percentage_complete  # Update the progress property
                self.report({'INFO'}, f"Percentage Complete: {percentage_complete:.2f}%")



                 # Render and save image
                scene.render.filepath = f"{dir_path}/{turntable_props.prefix}_{render_pass}_{angle}"
                bpy.ops.render.render(write_still=True)
                bpy.data.images['Render Result'].save_render(filepath=f"{dir_path}/{turntable_props.prefix}_{render_pass}_{angle}.png")

        # Restore original connections
        for from_socket, to_socket in original_links:
            tree.links.new(from_socket, to_socket)

        # Delete created nodes
        for node_name in created_nodes:
            if node_name in tree.nodes.keys():  # Check if the node still exists
                tree.nodes.remove(tree.nodes[node_name])

        # Delete circle and restore original settings
        bpy.data.objects.remove(circle, do_unlink=True)  # Added do_unlink=True to remove the circle
        context.scene.camera.parent = original_camera_parent
        scene.view_layers["0: Combined"].use_pass_z = original_pass_z
        scene.view_layers["0: Combined"].use_pass_normal = original_pass_normal

        # Restore original settings
        scene.render.image_settings.file_format = original_file_format
        scene.render.filepath = original_filepath

        bpy.context.window_manager.progress_end()

        return {'FINISHED'}
    
def timer_update():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()

    
# To support reload properly, try to access a package var, if it's there, reload everything
def cleanse_modules():
    """search for your plugin modules in blender python sys.modules and remove them"""

    import sys

    all_modules = sys.modules 
    all_modules = dict(sorted(all_modules.items(),key= lambda x:x[0])) #sort them
   
    for k,v in all_modules.items():
        if k.startswith(__name__):
            del sys.modules[k]

    return None 

def register():
    bpy.utils.register_class(TurntableRenderProperties)
    bpy.utils.register_class(TurntableRenderPanel)
    bpy.utils.register_class(TurntableRenderOperator)
    bpy.types.Scene.turntable_props = bpy.props.PointerProperty(type=TurntableRenderProperties)
    bpy.app.timers.register(timer_update, persistent=True)


def unregister():
    bpy.utils.unregister_class(TurntableRenderProperties)
    bpy.utils.unregister_class(TurntableRenderPanel)
    bpy.utils.unregister_class(TurntableRenderOperator)
    del bpy.types.Scene.turntable_props

    cleanse_modules()

if __name__ == "__main__":
    register()
