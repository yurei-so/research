package so.yurei.voxelguidance;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.fabricmc.loader.api.FabricLoader;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

final class OwnershipGate {
    static final String INSTANCE_ID = "Voxel Guidance Lab";
    private static final String GROUP = "Prism Toolkit";

    private OwnershipGate() {}

    static Path requireOwnedGameDirectory() throws IOException {
        Path game = FabricLoader.getInstance().getGameDir().toRealPath();
        Path instance = game.getParent();
        if (instance == null || !INSTANCE_ID.equals(instance.getFileName().toString())) {
            throw new IOException("not running inside the Voxel Guidance Lab instance");
        }
        Path instances = instance.getParent();
        Path root = instances == null ? null : instances.getParent();
        if (root == null) throw new IOException("cannot resolve Prism root");

        JsonObject marker = object(instance.resolve(".prism-toolkit-owned.json"));
        JsonObject registry = object(root.resolve(".prism-toolkit/registry.json"));
        JsonObject groups = object(instances.resolve("instgroups.json"));
        String markerId = string(marker, "markerId");
        if (!INSTANCE_ID.equals(string(marker, "instanceId"))) throw new IOException("ownership marker mismatch");
        JsonObject registered = registry.getAsJsonObject("instances").getAsJsonObject(INSTANCE_ID);
        if (registered == null || !markerId.equals(string(registered, "markerId"))) {
            throw new IOException("toolkit registry mismatch");
        }
        JsonObject group = groups.getAsJsonObject("groups").getAsJsonObject(GROUP);
        if (group == null || !group.getAsJsonArray("instances").asList().stream()
                .anyMatch(value -> INSTANCE_ID.equals(value.getAsString()))) {
            throw new IOException("Prism Toolkit group membership missing");
        }
        return game;
    }

    private static JsonObject object(Path path) throws IOException {
        try (var reader = Files.newBufferedReader(path)) {
            return JsonParser.parseReader(reader).getAsJsonObject();
        } catch (RuntimeException error) {
            throw new IOException("invalid ownership record: " + path.getFileName(), error);
        }
    }

    private static String string(JsonObject object, String key) throws IOException {
        if (object == null || !object.has(key) || !object.get(key).isJsonPrimitive()) {
            throw new IOException("ownership record missing " + key);
        }
        return object.get(key).getAsString();
    }
}

