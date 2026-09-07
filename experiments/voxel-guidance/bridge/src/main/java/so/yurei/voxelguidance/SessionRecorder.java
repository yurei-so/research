package so.yurei.voxelguidance;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;

import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.PosixFilePermissions;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;

final class SessionRecorder {
    private static final Gson GSON = new Gson();
    private static final Pattern ID = Pattern.compile("[a-z0-9][a-z0-9._-]{0,63}");
    private static final Set<String> MARKERS = Set.of(
            "plan_started", "plan_revised", "setback", "recovered", "task_complete");
    private BufferedWriter writer;
    private String sessionId;
    private String taskId;
    private int sequence;
    private int ticks;

    synchronized void start(Minecraft client, String task, String protocol) throws IOException {
        if (writer != null) throw new IOException("a recording is already active");
        if (!ID.matcher(task).matches() || !ID.matcher(protocol).matches()) {
            throw new IOException("task and protocol IDs must use lowercase letters, digits, dot, dash, or underscore");
        }
        Path game = OwnershipGate.requireOwnedGameDirectory();
        Path directory = game.resolve(".voxel-guidance/private/sessions");
        Files.createDirectories(directory);
        try { Files.setPosixFilePermissions(directory, PosixFilePermissions.fromString("rwx------")); }
        catch (UnsupportedOperationException ignored) {}
        sessionId = UUID.randomUUID().toString();
        taskId = task;
        sequence = 0;
        ticks = 0;
        Path output = directory.resolve(sessionId + ".ndjson");
        writer = Files.newBufferedWriter(output, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
        try { Files.setPosixFilePermissions(output, PosixFilePermissions.fromString("rw-------")); }
        catch (UnsupportedOperationException ignored) {}
        write("session_start", payload("protocol_id", protocol));
        notify(client, "recording " + task);
    }

    synchronized void marker(Minecraft client, String marker) throws IOException {
        requireActive();
        if (!MARKERS.contains(marker)) throw new IOException("unknown marker");
        write("marker", payload("marker", marker));
        notify(client, "marked " + marker);
    }

    synchronized void stop(Minecraft client, String reason) throws IOException {
        requireActive();
        try { write("session_end", payload("reason", reason)); }
        finally { writer.close(); writer = null; }
        notify(client, "recording stopped");
    }

    synchronized void tick(Minecraft client) {
        if (writer == null || client.player == null || client.level == null) return;
        ticks++;
        if (ticks % 20 != 0) return;
        try {
            String dimension = switch (client.level.dimension().location().getPath()) {
                case "the_nether" -> "nether";
                case "the_end" -> "end";
                default -> "overworld";
            };
            JsonObject payload = new JsonObject();
            payload.addProperty("x", client.player.getX());
            payload.addProperty("y", client.player.getY());
            payload.addProperty("z", client.player.getZ());
            payload.addProperty("dimension", dimension);
            write("position_sample", payload);
            notify(client, "RECORDING " + taskId);
        } catch (IOException error) {
            fail(client, error);
        }
    }

    synchronized void disconnect(Minecraft client) {
        if (writer == null) return;
        try { stop(client, "stopped"); }
        catch (IOException error) { fail(client, error); }
    }

    synchronized boolean active() { return writer != null; }

    private void requireActive() throws IOException {
        if (writer == null) throw new IOException("no recording is active");
    }

    private void write(String kind, JsonObject payload) throws IOException {
        JsonObject event = new JsonObject();
        event.addProperty("format", "voxel-guidance.event");
        event.addProperty("version", 1);
        event.addProperty("session_id", sessionId);
        event.addProperty("sequence", sequence++);
        event.addProperty("observed_at", Instant.now().truncatedTo(ChronoUnit.MILLIS).toString());
        event.addProperty("instance_id", OwnershipGate.INSTANCE_ID);
        event.addProperty("task_id", taskId);
        event.addProperty("kind", kind);
        event.add("payload", payload);
        writer.write(GSON.toJson(event));
        writer.newLine();
        writer.flush();
    }

    private static JsonObject payload(String key, String value) {
        JsonObject payload = new JsonObject();
        payload.addProperty(key, value);
        return payload;
    }

    private void fail(Minecraft client, IOException error) {
        try { if (writer != null) writer.close(); } catch (IOException ignored) {}
        writer = null;
        notify(client, "recording failed: " + error.getMessage());
    }

    static void notify(Minecraft client, String message) {
        if (client.player != null) client.player.displayClientMessage(Component.literal("[Voxel Guidance] " + message), true);
    }
}

