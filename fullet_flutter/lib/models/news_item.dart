class NewsItem {
  final String title;
  final String link;
  final String source;
  final DateTime? date;

  const NewsItem({
    required this.title,
    required this.link,
    required this.source,
    required this.date,
  });

  factory NewsItem.fromJson(Map<String, dynamic> json) {
    return NewsItem(
      title: json['baslik']?.toString() ?? '',
      link: json['link']?.toString() ?? '',
      source: json['kaynak']?.toString() ?? 'Haber',
      date: DateTime.tryParse(json['tarih']?.toString() ?? ''),
    );
  }
}
