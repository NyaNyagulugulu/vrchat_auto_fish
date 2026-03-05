package vrchat.FantasyNetwork;

import java.awt.*;
import java.awt.image.BufferedImage;

public class WindowCapture {
    private volatile boolean running = false;
    private String windowTitle;
    private Rectangle windowBounds;
    private Robot robot;
    private FrameCallback frameCallback;

    public interface FrameCallback {
        void onFrame(BufferedImage frame);
    }

    public WindowCapture() {
        try {
            robot = new Robot();
        } catch (AWTException e) {
            e.printStackTrace();
        }
    }

    public void setWindowTitle(String title) {
        this.windowTitle = title;
    }

    public void setFrameCallback(FrameCallback callback) {
        this.frameCallback = callback;
    }

    public void start() {
        if (running) {
            return;
        }

        running = true;
        new Thread(this::captureLoop).start();
    }

    public void stop() {
        running = false;
    }

    private void captureLoop() {
        while (running) {
            try {
                if (findWindow()) {
                    BufferedImage frame = robot.createScreenCapture(windowBounds);
                    if (frameCallback != null) {
                        frameCallback.onFrame(frame);
                    }
                }
                Thread.sleep(33);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private boolean findWindow() {
        if (windowTitle == null || windowTitle.isEmpty()) {
            windowBounds = new Rectangle(Toolkit.getDefaultToolkit().getScreenSize());
            return true;
        }

        try {
            ProcessBuilder pb = new ProcessBuilder(
                "xdotool", "search", "--name", windowTitle
            );
            Process process = pb.start();

            java.io.BufferedReader reader = new java.io.BufferedReader(
                new java.io.InputStreamReader(process.getInputStream())
            );

            String line;
            java.util.List<String> windowIds = new java.util.ArrayList<>();
            
            while ((line = reader.readLine()) != null) {
                windowIds.add(line.trim());
            }

            int exitCode = process.waitFor();
            
            if (exitCode == 0 && !windowIds.isEmpty()) {
                Rectangle bestBounds = null;
                int maxArea = 0;
                
                for (String windowId : windowIds) {
                    try {
                        ProcessBuilder geomPb = new ProcessBuilder(
                            "xdotool", "getwindowgeometry", windowId
                        );
                        Process geomProcess = geomPb.start();
                        
                        java.io.BufferedReader geomReader = new java.io.BufferedReader(
                            new java.io.InputStreamReader(geomProcess.getInputStream())
                        );
                        
                        String geomLine;
                        int x = 0, y = 0, width = 0, height = 0;
                        
                        while ((geomLine = geomReader.readLine()) != null) {
                            if (geomLine.contains("Position:")) {
                                String posStr = geomLine.split(":")[1].trim();
                                posStr = posStr.split("\\(")[0].trim();
                                String[] coords = posStr.split(",");
                                x = Integer.parseInt(coords[0]);
                                y = Integer.parseInt(coords[1]);
                            }
                            if (geomLine.contains("Geometry:")) {
                                String geomStr = geomLine.split(":")[1].trim();
                                String[] dims = geomStr.split("x");
                                width = Integer.parseInt(dims[0]);
                                height = Integer.parseInt(dims[1]);
                            }
                        }
                        
                        geomProcess.waitFor();
                        
                        int area = width * height;
                        if (area > maxArea && area > 100) {
                            maxArea = area;
                            bestBounds = new Rectangle(x, y, width, height);
                        }
                    } catch (Exception e) {
                        // 忽略单个窗口的错误
                    }
                }
                
                if (bestBounds != null) {
                    windowBounds = bestBounds;
                    System.out.println("Found window with largest area: " + windowBounds);
                    return true;
                }
            }
            
            System.out.println("No suitable window found, using full screen");
            windowBounds = new Rectangle(Toolkit.getDefaultToolkit().getScreenSize());
            return true;

        } catch (Exception e) {
            e.printStackTrace();
            windowBounds = new Rectangle(Toolkit.getDefaultToolkit().getScreenSize());
            return true;
        }
    }

    public Rectangle getWindowBounds() {
        return windowBounds;
    }
}