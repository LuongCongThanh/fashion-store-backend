# Sự kiện giữa các module: Outbox + Celery trên Redis, chưa dùng Kafka

Sự kiện giữa các module (`OrderPlaced`, `PaymentSucceeded`…) được ghi vào outbox trong cùng transaction với dữ liệu nghiệp vụ. PostgreSQL lưu từng cặp sự kiện–handler trong `EventDelivery`, gồm trạng thái, lịch retry và hạn giao lại. Relay chạy độc lập với Celery Beat để giao các cặp còn chờ qua Redis; enqueue thành công không được coi là handler hoàn tất. Consumer khoá delivery và chuyển trạng thái của nó cùng transaction với tác động DB của handler. Bản thân `EventDelivery` là dấu "đã xử lý" và nơi lưu lỗi khi hết retry; không có bảng riêng cho sự kiện đã xử lý hay sự kiện lỗi, vì cả hai luôn được ghi cùng transaction với trạng thái delivery và chỉ lặp lại thông tin đó. Mọi việc gửi và nhận sự kiện đi qua `common/events/`.

Email được ghi thành `EmailLog` còn chờ trong transaction của handler; task gửi ngoài transaction, có lease và job quét lại. Chọn lưu công việc bền vững trong PostgreSQL thay vì chỉ dựa vào `on_commit` hoặc Redis để khôi phục khi process chết hay broker mất task. Đánh đổi là thêm bảng trạng thái, quét định kỳ và chi phí vận hành. Chi tiết tại [07-async-events-jobs.md](../architecture/07-async-events-jobs.md).

Lý do chưa dùng Kafka: ở tải MVP (khoảng 10k–200k sự kiện/ngày), MSK tại Singapore tốn khoảng 87–730 USD/tháng và cần người vận hành, trong khi Celery trên Redis không phát sinh thêm chi phí và chạy giống hệt nhau ở local và trên AWS.

## Các phương án đã cân nhắc

- **Kafka ở cả local và AWS (MSK)**: chưa chọn vì chi phí và công vận hành không tương xứng với quy mô hiện tại.
- **Kafka ở local, SNS+SQS trên AWS**: không chọn, vì local và production chạy hai công nghệ khác nhau, dễ sinh lỗi chỉ có trên production.

## Hệ quả

- Không có đảm bảo thứ tự sự kiện. Handler báo cho consumer biết sự kiện tới sớm (ném `RetryLater`, consumer thử lại sau) hay không áp dụng được (ném `DomainError`, consumer bỏ qua và ghi log). Với Đơn hàng, việc phân loại này nằm trong các transition của máy trạng thái, nên handler không phải tự kiểm tra trạng thái.
- Không replay được sự kiện qua broker. Nếu cần, bảng `outbox` đóng vai event log.
- Giao task có thể lặp; chống trùng chỉ bảo vệ tác động DB trong transaction của cùng cặp sự kiện–handler. Gửi email ra nhà cung cấp có thể trùng nếu họ đã nhận nhưng chưa lưu `sent`; không hứa xử lý bên ngoài đúng một lần.
- Không xoá sự kiện còn delivery `pending`/`failed` khi purge; retry và lệnh khôi phục dựa vào trạng thái PostgreSQL, không dựa vào Redis.
- Code nghiệp vụ enqueue qua `common.tasks.enqueue_on_commit`; hạ tầng relay có thể gọi broker trực tiếp. Task quan trọng phải có bản ghi công việc trong DB và cơ chế quét lại; `on_commit` chỉ giúp giảm độ trễ.

## Hướng mở rộng

- **Chuyển sang Kafka** khi có một trong các điều kiện: lưu lượng vượt khoảng 1.000 sự kiện/giây liên tục, cần phát lại lịch sử cho hệ thống mới (analytics, search, CDC), cần stream processing, hoặc có người vận hành Kafka. Khi đó chỉ cần viết thêm một adapter `EventPublisher` cho Kafka, với tên topic theo dạng `<module>.<event>.v<version>` và client `confluent-kafka`.
- **Schema Registry** chỉ cần khi dùng Kafka và có nhiều service hoặc team độc lập. Vì sự kiện đã là class Pydantic có version, việc bổ sung ước tính khoảng 3–5 ngày công nếu dùng JSON Schema.
