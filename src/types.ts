export interface TorrentResult {
  Id: number;
  Tracker: string;
  CategoryDesc: string;
  Title: string;
  Link: string;
  Details: string;
  MagnetUri: string | null;
  InfoHash: string | null;
  Size: number;
  Seeders: number;
  Peers: number;
  PublishDate: string;
}

export interface Category {
  id: string;
  name: string;
}
