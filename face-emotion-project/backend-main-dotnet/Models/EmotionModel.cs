namespace BackendMainDotnet.Models
{
    public class BoundingBoxModel
    {
        public float Xmin { get; set; }
        public float Ymin { get; set; }
        public float Xmax { get; set; }
        public float Ymax { get; set; }
    }

    public class EmotionDetectionResult
    {
        public string Emotion { get; set; } = "Neutral";
        public float Confidence { get; set; }
        public BoundingBoxModel BoundingBox { get; set; } = new BoundingBoxModel();
    }
}
