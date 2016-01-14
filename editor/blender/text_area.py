from itertools import chain

import bpy


class BlenderTextArea:

    def __init__(self, name):
        self.on_write = None
        self.on_read = None
        self.write_on_edit = False

        self._name = name

        self._text = ""

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, text):
        invoke_writer = self.write_on_edit and text != self._text

        self._text = text

        if invoke_writer and callable(self.on_write):
            self.on_write(text)

    @property
    def name(self):
        return self._name

    def on_opened(self):
        if callable(self.on_read):
            self._text = self.on_read()

    def on_closed(self):
        if callable(self.on_write):
            self.on_write(self._text)


class BlenderTextAreaManager:

    def __init__(self):
        self._active_area = None
        self._text_block = None

        self.clear_text_areas()

    def clear_text_areas(self):
        to_delete = []

        for text_block in bpy.data.texts:
            if "TextArea" in text_block.name:
                to_delete.append(text_block)

        for text_block in to_delete:
            bpy.data.texts.remove(text_block)

    @property
    def active_area(self):
        return self._active_area

    @active_area.setter
    def active_area(self, area):
        # If area already open
        if self._active_area:
            self._active_area.on_closed()

            # Delete text block
            self.clear_text_areas()
            self._text_block = None

        # If new area is a text area
        self._active_area = area

        if area is not None:
            # Create text block
            self._text_block = bpy.data.texts.new("<TextArea: {}>".format(area.name))

            # Switch to editor
            self._display_text_area(self._text_block)

            # Open area
            area.on_opened()

            # Display loaded text
            self._text_block.from_string(area.text)

    def _display_text_area(self, block):
        blender_text_areas = []
        blender_other_areas = []

        # Find all open areas
        for area in bpy.context.screen.areas:
            if area.type == "NODE_EDITOR":
                continue

            area_list = blender_text_areas if area.type == 'TEXT_EDITOR' else blender_other_areas
            area_list.append((area, area.height * area.width))

        # First try to find a Text Editor area, then a non-Text Editor
        blender_text_areas.sort(key=lambda x: x[-1], reverse=True)
        blender_other_areas.sort(key=lambda x: x[-1], reverse=True)

        try:
            area = next(chain(blender_text_areas, blender_other_areas))[0]

        except StopIteration:
            raise RuntimeError("No Areas!")

        space = area.spaces[0]

        # Configure window
        area.type = 'TEXT_EDITOR'
        space.text = block

    def update(self):
        active_area = self._active_area
        if active_area is None:
            return

        # Text block deleted, unset area
        if self._text_block.name not in bpy.data.texts:
            self.active_area = None

        # Update text
        else:
            active_area.text = self._text_block.as_string()


